from __future__ import annotations

from app.core.llm import PromptPackage, complete_prompt
from app.domain.schemas import Evidence
from app.online.reasoning import build_reasoning_summary
from app.prompts import render_prompt


def _format_evidence_lines(evidence: list[Evidence]) -> list[str]:
    return [f"- [{item.source}] {item.content} (score={item.score:.3f})" for item in evidence]


def generate_final_answer(state: dict) -> dict:
    evidence = [item if isinstance(item, Evidence) else Evidence(**item) for item in state.get("reranked_evidence", [])[:3]]
    reasoning_summary = build_reasoning_summary(state)
    prompt_text = render_prompt(
        "safe_answer",
        question=state.get("question", ""),
        risk_level=state.get("risk_level", "low"),
        fallback_mode=state.get("fallback_mode", "none"),
        reasoning_summary=reasoning_summary,
    )
    llm_result = complete_prompt(role="answer", prompt=PromptPackage(system="你是审慎的知识问答代理，请严格基于证据回答。", user=prompt_text))
    if llm_result.content.strip():
        answer = llm_result.content.strip()
    elif not evidence:
        answer = "当前没有检索到足够证据，暂时不能给出可靠结论。请补充更明确的现象、部件名称、问题编号或历史报告。"
    elif state.get("fallback_mode") == "summary_only":
        answer = "当前证据仍不足以支持强结论，以下给出保守摘要。\n" + "\n".join(_format_evidence_lines(evidence))
    elif state.get("fallback_mode") == "conflict_notice":
        answer = "现有证据之间存在冲突，暂不建议直接下最终判断。\n" + "\n".join(_format_evidence_lines(evidence))
    else:
        answer = "基于当前证据，优先关注以下方向。\n" + "\n".join(_format_evidence_lines(evidence))
    payload = {
        "answer": answer,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "reasoning_path": state.get("reasoning_path", []),
        "reasoning_summary": reasoning_summary,
        "answer_model": llm_result.model,
        "answer_provider": llm_result.provider,
        "answer_fallback": llm_result.used_fallback,
        "prompt_blueprint_length": len(prompt_text),
    }
    return {"final_answer": answer, "answer_payload": payload}

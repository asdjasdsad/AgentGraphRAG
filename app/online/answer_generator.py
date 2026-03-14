from __future__ import annotations

from app.domain.schemas import Evidence
from app.online.reasoning import build_reasoning_summary
from app.prompts import render_prompt


def _format_evidence_lines(evidence: list[Evidence]) -> list[str]:
    return [f"- [{item.source}] {item.content} (score={item.score:.3f})" for item in evidence]


def generate_final_answer(state: dict) -> dict:
    evidence = [
        item if isinstance(item, Evidence) else Evidence(**item)
        for item in state.get("reranked_evidence", [])[:3]
    ]
    reasoning_summary = build_reasoning_summary(state)
    prompt_blueprint = render_prompt(
        "safe_answer",
        question=state.get("question", ""),
        risk_level=state.get("risk_level", "low"),
        fallback_mode=state.get("fallback_mode", "none"),
        reasoning_summary=reasoning_summary,
    )

    if not evidence:
        answer = (
            "结论：当前没有检索到足够证据，暂时不能给出可靠结论。\n"
            "关键证据：暂无可用证据。\n"
            "建议动作：请补充更明确的故障现象、部件名称、问题编号或历史报告。"
        )
    elif state.get("fallback_mode") == "summary_only":
        answer = (
            "结论：当前证据还不足以支撑强结论，只能给出保守摘要。\n"
            f"关键证据：\n{chr(10).join(_format_evidence_lines(evidence))}\n"
            "建议动作：补充历史案例、图关系路径或更精准的问题约束后再检索。"
        )
    elif state.get("fallback_mode") == "conflict_notice":
        answer = (
            "结论：现有证据之间存在冲突，暂不建议直接下最终判断。\n"
            f"关键证据：\n{chr(10).join(_format_evidence_lines(evidence))}\n"
            "建议动作：建议人工复核原始文档、页码和责任链路，再确认最终结论。"
        )
    else:
        answer = (
            "结论：基于当前命中的证据，较高概率的分析方向如下。\n"
            f"关键证据：\n{chr(10).join(_format_evidence_lines(evidence))}\n"
            f"建议动作：优先沿着“{state.get('relation_type') or '相关链路'}”继续核验，并结合图谱路径做复查。"
        )

    payload = {
        "answer": answer,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "reasoning_path": state.get("reasoning_path", []),
        "reasoning_summary": reasoning_summary,
        "prompt_blueprint_length": len(prompt_blueprint),
    }
    return {"final_answer": answer, "answer_payload": payload}

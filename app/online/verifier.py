from __future__ import annotations

from app.domain.enums import RiskLevel
from app.domain.schemas import Evidence
from app.prompts import render_prompt


def verify_evidence(state: dict) -> dict:
    evidence = [
        item if isinstance(item, Evidence) else Evidence(**item)
        for item in state.get("reranked_evidence", [])
    ]
    risk_level = state.get("risk_level", RiskLevel.LOW)
    top_evidence = evidence[:3]
    prompt_blueprint = render_prompt(
        "verify_evidence",
        question=state.get("question", ""),
        risk_level=risk_level,
        top_evidence=[f"{item.source}:{item.score:.3f}:{item.content}" for item in top_evidence],
    )

    top_score = top_evidence[0].score if top_evidence else 0.0
    unique_sources = {item.source for item in top_evidence}
    entity_coverage = sum(
        1
        for entity in state.get("entities", [])
        if any(entity in item.content for item in top_evidence)
    )
    conflict_detected = any(keyword in item.content for item in top_evidence for keyword in ("冲突", "矛盾", "不一致"))

    sufficient_threshold = 0.88 if risk_level == RiskLevel.HIGH else 0.78 if risk_level == RiskLevel.MEDIUM else 0.68
    is_sufficient = bool(
        top_evidence
        and (
            len(top_evidence) >= 2
            and top_score >= sufficient_threshold
            and (entity_coverage >= 1 or len(unique_sources) >= 2)
        )
    )

    fallback_mode = "none"
    if conflict_detected:
        fallback_mode = "conflict_notice"
    elif not is_sufficient:
        fallback_mode = "summary_only"

    verification_notes = [
        f"最高证据分 {top_score:.3f}，命中来源 {len(unique_sources)} 个，实体覆盖 {entity_coverage}。",
        f"风险等级 {risk_level} 对应充分阈值 {sufficient_threshold:.2f}。",
        f"校验提示词已加载，长度 {len(prompt_blueprint)} 字符。",
    ]
    if conflict_detected:
        verification_notes.append("前排证据中发现冲突信号，答案会降级为 conflict_notice。")
    elif not is_sufficient:
        verification_notes.append("当前证据不足以支撑强结论，答案会降级为 summary_only。")
    else:
        verification_notes.append("证据数量、分数和覆盖度达到返回正式结论的最低要求。")

    return {
        "is_sufficient": is_sufficient,
        "conflict_detected": conflict_detected,
        "fallback_mode": fallback_mode,
        "verification_notes": verification_notes,
    }

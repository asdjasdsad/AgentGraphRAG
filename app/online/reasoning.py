from __future__ import annotations

from app.domain.schemas import Evidence


def build_reasoning_summary(state: dict) -> list[str]:
    summaries: list[str] = []
    route_reason = state.get("route_reason")
    if route_reason:
        summaries.append(f"检索路由：{route_reason}")

    for evidence in state.get("reranked_evidence", [])[:3]:
        item = evidence if isinstance(evidence, Evidence) else Evidence(**evidence)
        summaries.append(f"证据 {item.evidence_id} 来自 {item.source}，得分 {item.score:.3f}，内容摘要：{item.content}")

    for note in state.get("verification_notes", [])[:2]:
        summaries.append(f"校验结论：{note}")
    return summaries

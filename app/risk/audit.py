from __future__ import annotations

from app.core.db_mysql import audit_logs_table
from app.domain.schemas import AuditLog, QAState


def write_audit_log(state: QAState) -> dict:
    log = AuditLog(
        trace_id=state.trace_id,
        user_id=state.user_id,
        question=state.question,
        route=state.retrieval_strategy.value,
        risk_level=state.risk_level,
        final_answer=state.final_answer,
        evidence_ids=[item.evidence_id for item in state.reranked_evidence[:5]],
        fallback_mode=state.fallback_mode,
        agent_traces=state.agent_traces,
        reasoning_path=state.reasoning_path,
        answer_payload=state.answer_payload,
    )
    return audit_logs_table.upsert(log, "trace_id")

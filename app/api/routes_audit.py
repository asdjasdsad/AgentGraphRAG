from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.db_mysql import audit_logs_table


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs(limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    rows = sorted(audit_logs_table.all(), key=lambda item: item.get("created_at", ""), reverse=True)
    return rows[:limit]


@router.get("/logs/{trace_id}")
def get_audit_log(trace_id: str) -> dict:
    row = audit_logs_table.get(trace_id=trace_id)
    if not row:
        raise HTTPException(status_code=404, detail="trace not found")
    return row

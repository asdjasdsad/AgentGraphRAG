from __future__ import annotations

from fastapi import APIRouter

from app.core.db_mysql import audit_logs_table


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs() -> list[dict]:
    return audit_logs_table.all()

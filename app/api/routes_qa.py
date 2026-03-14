from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.db_mysql import audit_logs_table
from app.domain.schemas import AskRequest, AskResponse
from app.online.workflow import workflow


router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    return workflow.run(request)


@router.get("/trace/{trace_id}")
def get_trace(trace_id: str) -> dict:
    row = audit_logs_table.get(trace_id=trace_id)
    if not row:
        raise HTTPException(status_code=404, detail="trace not found")
    return row

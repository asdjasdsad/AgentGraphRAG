from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.memory.case_memory import case_memory


router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/search")
def search_cases(payload: dict) -> list[dict]:
    query = payload.get("query", "")
    return case_memory.search(query)


@router.get("/{case_id}")
def get_case(case_id: str) -> dict:
    case = case_memory.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="case not found")
    return case

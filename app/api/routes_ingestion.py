from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.db_mysql import documents_table, jobs_table
from app.domain.schemas import DocumentMetadata
from app.offline.tasks import create_job, run_job


router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/start")
def start_ingestion(payload: dict) -> dict:
    if payload.get("source_type") == "structured":
        job = create_job("structured", {"records": payload.get("records", [])})
    else:
        document_row = documents_table.get(document_id=payload["document_id"])
        if not document_row:
            raise HTTPException(status_code=404, detail="document not found")
        job = create_job("document", {"document": DocumentMetadata(**document_row).model_dump(mode="json")})
    result = run_job(job.job_id)
    return result


@router.get("")
def list_jobs(limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    rows = sorted(jobs_table.all(), key=lambda item: item.get("created_at", ""), reverse=True)
    return rows[:limit]


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    row = jobs_table.get(job_id=job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row


@router.post("/{job_id}/retry")
def retry_job(job_id: str) -> dict:
    try:
        return run_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

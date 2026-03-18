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


@router.post("/structured-records")
def ingest_structured_payload(payload: dict) -> dict:
    records = payload.get("records", [])
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="records must be a non-empty list")
    source_system = str(payload.get("source_system", "api") or "api")
    normalized_records: list[dict] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise HTTPException(status_code=400, detail=f"record at index {index} must be an object")
        issue_id = str(record.get("issue_id", "")).strip()
        phenomenon = str(record.get("phenomenon", "")).strip()
        if not issue_id or not phenomenon:
            raise HTTPException(status_code=400, detail=f"record at index {index} requires issue_id and phenomenon")
        normalized_records.append(
            {
                **record,
                "source_type": "structured",
                "source_system": str(record.get("source_system", source_system) or source_system),
            }
        )
    job = create_job("structured", {"records": normalized_records, "source_system": source_system})
    result = run_job(job.job_id)
    return {
        "job": result["job"],
        "result": result["result"],
        "accepted_records": len(normalized_records),
        "source_system": source_system,
        "api_hint": {
            "endpoint": "/api/v1/ingestion/structured-records",
            "method": "POST",
        },
    }


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

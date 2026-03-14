from __future__ import annotations

from datetime import datetime

from app.core.db_mysql import jobs_table
from app.domain.enums import JobStatus
from app.domain.schemas import IngestionJob
from app.offline.ingest_structured import ingest_structured_records
from app.offline.ingest_unstructured import ingest_document


def create_job(source_type: str, payload: dict) -> IngestionJob:
    job = IngestionJob(source_type=source_type, payload=payload)
    jobs_table.upsert(job, "job_id")
    return job


def run_job(job_id: str) -> dict:
    row = jobs_table.get(job_id=job_id)
    if not row:
        raise ValueError(f"job not found: {job_id}")
    job = IngestionJob(**row)
    job.status = JobStatus.RUNNING
    jobs_table.upsert(job, "job_id")
    try:
        if job.source_type == "structured":
            result = ingest_structured_records(job.payload.get("records", []), load_batch_id=job.batch_id)
        else:
            result = ingest_document(job.payload["document"], load_batch_id=job.batch_id)
        job.status = JobStatus.SUCCESS
        job.finished_at = datetime.utcnow()
        jobs_table.upsert(job, "job_id")
        return {"job": job.model_dump(mode="json"), "result": result}
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()
        jobs_table.upsert(job, "job_id")
        raise

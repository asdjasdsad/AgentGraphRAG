from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.core.config import get_settings
from app.core.db_mysql import chunks_table, documents_table
from app.domain.schemas import DocumentMetadata, DocumentUploadResponse


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    settings = get_settings()
    document = DocumentMetadata(file_name=file.filename or "unknown", file_type=Path(file.filename or "").suffix.lower())
    target = settings.upload_dir / f"{document.document_id}_{file.filename}"
    content = await file.read()
    target.write_bytes(content)
    document.storage_path = str(target)
    documents_table.upsert(document, "document_id")
    return DocumentUploadResponse(
        document_id=document.document_id,
        file_name=document.file_name,
        storage_path=str(target),
        status="uploaded",
    )


@router.get("")
def list_documents(limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    rows = sorted(documents_table.all(), key=lambda item: item.get("upload_time", ""), reverse=True)
    return rows[:limit]


@router.get("/{document_id}")
def get_document(document_id: str) -> dict:
    row = documents_table.get(document_id=document_id)
    if not row:
        raise HTTPException(status_code=404, detail="document not found")
    chunk_count = len(chunks_table.filter(document_id=document_id))
    payload = dict(row)
    payload["chunk_count"] = chunk_count
    return payload


@router.get("/{document_id}/chunks")
def get_document_chunks(document_id: str, limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    rows = chunks_table.filter(document_id=document_id)
    rows = sorted(rows, key=lambda item: (item.get("page_no") or 0, item.get("section_path", ""), item.get("chunk_id", "")))
    return rows[:limit]

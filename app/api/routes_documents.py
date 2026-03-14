from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.core.config import get_settings
from app.core.db_mysql import documents_table
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

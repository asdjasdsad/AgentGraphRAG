from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.db_milvus import milvus_store
from app.core.db_mysql import cases_table, chunks_table, documents_table
from app.core.db_neo4j import graph_store


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/chunks")
def list_chunks(document_id: str | None = None, limit: int = 200) -> list[dict]:
    rows = chunks_table.filter(document_id=document_id) if document_id else chunks_table.all()
    rows = sorted(rows, key=lambda item: (item.get("document_id", ""), item.get("page_no") or 0, item.get("section_path", "")))
    return rows[:limit]


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str) -> dict:
    row = chunks_table.get(chunk_id=chunk_id)
    if not row:
        raise HTTPException(status_code=404, detail="chunk not found")
    return row


@router.get("/cases")
def list_case_memory(limit: int = 100) -> list[dict]:
    rows = sorted(cases_table.all(), key=lambda item: item.get("case_id", ""))
    return rows[:limit]


@router.get("/graph")
def graph_snapshot(limit: int = 200) -> dict:
    return graph_store.snapshot(limit=limit)


@router.get("/storage/status")
def storage_status() -> dict:
    return {
        "documents": {"count": len(documents_table.all())},
        "chunks": {"count": len(chunks_table.all())},
        "cases": {"count": len(cases_table.all())},
        "milvus": milvus_store.storage_status(),
        "neo4j": graph_store.storage_status(),
    }

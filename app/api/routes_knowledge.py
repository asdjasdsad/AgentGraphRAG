from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.db_mysql import chunks_table
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


@router.get("/graph")
def graph_snapshot(limit: int = 200) -> dict:
    return graph_store.snapshot(limit=limit)

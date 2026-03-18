from __future__ import annotations

from app.core.db_milvus import milvus_store


def search_vector_evidence(query: str, filters: dict | None = None, top_k: int = 5) -> list[dict]:
    return [item.model_dump(mode="json") for item in milvus_store.search(query, filters, top_k)]

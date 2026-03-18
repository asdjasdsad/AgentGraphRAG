from __future__ import annotations

from app.core.db_milvus import milvus_store


class SemanticMemory:
    def search(self, query: str, top_k: int = 3) -> list[dict]:
        return [item.model_dump(mode="json") for item in milvus_store.search(query, top_k=top_k)]


semantic_memory = SemanticMemory()

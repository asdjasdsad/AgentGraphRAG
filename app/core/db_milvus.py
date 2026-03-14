from __future__ import annotations

import math
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from pymilvus import MilvusClient

from app.core.config import Settings, get_settings
from app.core.db_mysql import chunks_table
from app.core.embeddings import embed_documents, embed_query
from app.domain.schemas import Chunk, Evidence


DEFAULT_VECTOR_FIELD = "vector"
DEFAULT_ID_FIELD = "id"
DEFAULT_SEARCH_FIELDS = [
    "content",
    "document_id",
    "doc_type",
    "chunk_type",
    "section_path",
    "page_no",
    "issue_id",
    "source_type",
    "load_batch_id",
]


def reset_milvus_clients() -> None:
    get_milvus_client.cache_clear()


@lru_cache(maxsize=4)
def get_milvus_client(uri: str, token: str, database: str) -> MilvusClient:
    kwargs: dict[str, Any] = {"uri": uri}
    if token:
        kwargs["token"] = token
    if database:
        kwargs["db_name"] = database
    return MilvusClient(**kwargs)


def _cosine(a: Iterable[float], b: Iterable[float]) -> float:
    left = list(a)
    right = list(b)
    return sum(x * y for x, y in zip(left, right))


def _is_test_mode(settings: Settings) -> bool:
    return settings.app_env == "test"


def _quote_filter_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_filter_expression(metadata_filter: dict[str, Any]) -> str | None:
    expressions = [f"{field} == {_quote_filter_value(value)}" for field, value in metadata_filter.items() if value not in (None, "")]
    return " and ".join(expressions) or None


class MilvusStore:
    def _settings(self) -> Settings:
        return get_settings()

    def _client(self) -> MilvusClient:
        settings = self._settings()
        return get_milvus_client(settings.milvus_uri, settings.milvus_token, settings.milvus_database)

    def _ensure_collection(self) -> None:
        settings = self._settings()
        client = self._client()
        if client.has_collection(collection_name=settings.milvus_collection):
            return
        client.create_collection(
            collection_name=settings.milvus_collection,
            dimension=settings.embedding_dimensions,
            metric_type="IP",
            auto_id=False,
            enable_dynamic_field=True,
        )

    def _upsert_metadata(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            payload = chunk.model_dump(mode="json")
            payload.pop("embedding", None)
            chunks_table.upsert(payload, "chunk_id")

    def _mock_insert_chunks(self, chunks: list[Chunk]) -> None:
        embeddings = embed_documents([chunk.content for chunk in chunks]) if chunks else []
        for chunk, embedding in zip(chunks, embeddings):
            payload = chunk.model_dump(mode="json")
            payload["embedding"] = embedding
            chunks_table.upsert(payload, "chunk_id")

    def _mock_search(self, query_text: str, metadata_filter: dict[str, Any] | None = None, top_k: int = 5) -> list[Evidence]:
        query_embedding = embed_query(query_text)
        metadata_filter = metadata_filter or {}
        hits: list[Evidence] = []
        for row in chunks_table.all():
            if any(row.get(key) != value for key, value in metadata_filter.items()):
                continue
            score = _cosine(query_embedding, row.get("embedding", []))
            hits.append(
                Evidence(
                    evidence_id=row["chunk_id"],
                    source="milvus",
                    content=row["content"],
                    score=score,
                    metadata=row,
                )
            )
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]

    def insert_chunks(self, chunks: list[Chunk]) -> None:
        settings = self._settings()
        if _is_test_mode(settings):
            self._mock_insert_chunks(chunks)
            return

        self._ensure_collection()
        embeddings = embed_documents([chunk.content for chunk in chunks]) if chunks else []
        rows = []
        for chunk, embedding in zip(chunks, embeddings):
            rows.append(
                {
                    DEFAULT_ID_FIELD: chunk.chunk_id,
                    DEFAULT_VECTOR_FIELD: embedding,
                    "content": chunk.content,
                    "document_id": chunk.document_id,
                    "doc_type": chunk.doc_type.value if hasattr(chunk.doc_type, "value") else chunk.doc_type,
                    "chunk_type": chunk.chunk_type.value if hasattr(chunk.chunk_type, "value") else chunk.chunk_type,
                    "section_path": chunk.section_path,
                    "page_no": chunk.page_no,
                    "issue_id": chunk.issue_id,
                    "source_type": chunk.source_type,
                    "load_batch_id": chunk.load_batch_id,
                }
            )
        if rows:
            self._client().upsert(collection_name=settings.milvus_collection, data=rows)
        self._upsert_metadata(chunks)

    def search(self, query_text: str, metadata_filter: dict[str, Any] | None = None, top_k: int = 5) -> list[Evidence]:
        settings = self._settings()
        metadata_filter = metadata_filter or {}
        if _is_test_mode(settings):
            return self._mock_search(query_text, metadata_filter, top_k)

        self._ensure_collection()
        query_embedding = embed_query(query_text)
        expression = _build_filter_expression(metadata_filter)
        raw_hits = self._client().search(
            collection_name=settings.milvus_collection,
            data=[query_embedding],
            filter=expression,
            limit=top_k,
            output_fields=DEFAULT_SEARCH_FIELDS,
        )
        hits: list[Evidence] = []
        for group in raw_hits:
            for item in group:
                entity = item.get("entity", {})
                chunk_id = item.get(DEFAULT_ID_FIELD) or entity.get(DEFAULT_ID_FIELD)
                mysql_row = chunks_table.get(chunk_id=chunk_id) if chunk_id else None
                metadata = dict(mysql_row or {})
                metadata.update(entity)
                hits.append(
                    Evidence(
                        evidence_id=chunk_id or f"milvus_{len(hits)}",
                        source="milvus",
                        content=entity.get("content", metadata.get("content", "")),
                        score=float(item.get("distance", 0.0)),
                        metadata=metadata,
                    )
                )
        return hits

    def ping(self) -> dict[str, Any]:
        settings = self._settings()
        if _is_test_mode(settings):
            return {"ok": True, "backend": "mock-milvus"}
        try:
            self._ensure_collection()
            self._client().list_collections()
            return {"ok": True, "backend": settings.milvus_uri, "collection": settings.milvus_collection}
        except Exception as exc:  # pragma: no cover - exercised in app runtime
            return {
                "ok": False,
                "backend": settings.milvus_uri,
                "collection": settings.milvus_collection,
                "error": str(exc),
            }


milvus_store = MilvusStore()

from __future__ import annotations

import logging
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from pymilvus import DataType, MilvusClient
from pymilvus.exceptions import DataNotMatchException, MilvusException

from app.core.config import Settings, get_settings
from app.core.db_mysql import cases_table, chunks_table
from app.core.embeddings import embed_documents, embed_query
from app.domain.schemas import CaseSummary, Chunk, Evidence


DEFAULT_VECTOR_FIELD = "vector"
DEFAULT_ID_FIELD = "id"
DEFAULT_ID_MAX_LENGTH = 128
logger = logging.getLogger(__name__)


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
    "summary",
    "issue_type",
]


def _normalize_datatype_name(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    name = getattr(value, "name", None)
    if name:
        return str(name).upper()
    text = str(value).upper()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text


class MilvusSchemaMismatchError(RuntimeError):
    def __init__(self, collection_name: str, field_name: str, data_type: str) -> None:
        self.collection_name = collection_name
        self.field_name = field_name
        self.data_type = data_type
        super().__init__(
            f"Milvus collection '{collection_name}' schema is incompatible: "
            f"primary field is '{field_name}' ({data_type}), expected '{DEFAULT_ID_FIELD}' (VARCHAR)."
        )


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

    def _build_schema(self) -> Any:
        settings = self._settings()
        client = self._client()
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(DEFAULT_ID_FIELD, DataType.VARCHAR, is_primary=True, max_length=DEFAULT_ID_MAX_LENGTH)
        schema.add_field(DEFAULT_VECTOR_FIELD, DataType.FLOAT_VECTOR, dim=settings.embedding_dimensions)
        return schema

    def _describe_collection(self, collection_name: str) -> dict[str, Any] | None:
        describe = getattr(self._client(), "describe_collection", None)
        if not callable(describe):
            return None
        try:
            data = describe(collection_name=collection_name)
        except TypeError:
            data = describe(collection_name)
        return data if isinstance(data, dict) else None

    def _extract_primary_field(self, collection_name: str) -> dict[str, Any] | None:
        description = self._describe_collection(collection_name)
        if not description:
            return None
        fields = description.get("fields")
        if not isinstance(fields, list):
            return None
        for field in fields:
            if isinstance(field, dict) and field.get("is_primary"):
                return field
        return None

    def _validate_collection_schema(self, collection_name: str) -> None:
        primary_field = self._extract_primary_field(collection_name)
        if not primary_field:
            return
        field_name = str(primary_field.get("name") or primary_field.get("field_name") or "UNKNOWN")
        data_type = _normalize_datatype_name(primary_field.get("type") or primary_field.get("data_type"))
        if field_name != DEFAULT_ID_FIELD or data_type != "VARCHAR":
            raise MilvusSchemaMismatchError(collection_name, field_name, data_type)

    def _handle_schema_mismatch(self, collection_name: str, exc: MilvusSchemaMismatchError) -> None:
        settings = self._settings()
        if not settings.milvus_auto_recreate_on_schema_mismatch:
            raise RuntimeError(f"{exc} Recreate the collection before ingestion.") from exc
        logger.warning(
            "Recreating Milvus collection '%s' because schema is incompatible: primary field '%s' (%s)",
            collection_name,
            exc.field_name,
            exc.data_type,
        )
        self.recreate_collection(collection_name)

    def _ensure_collection(self, collection_name: str) -> None:
        client = self._client()
        if client.has_collection(collection_name=collection_name):
            try:
                self._validate_collection_schema(collection_name)
            except MilvusSchemaMismatchError as exc:
                self._handle_schema_mismatch(collection_name, exc)
            return
        client.create_collection(collection_name=collection_name, schema=self._build_schema(), metric_type="IP")

    def _load_collection(self, collection_name: str) -> None:
        load = getattr(self._client(), "load_collection", None)
        if not callable(load):
            return
        try:
            load(collection_name=collection_name)
        except TypeError:
            load(collection_name)

    def _ensure_collection_loaded(self, collection_name: str) -> None:
        self._ensure_collection(collection_name)
        self._load_collection(collection_name)

    def recreate_collection(self, collection_name: str) -> None:
        client = self._client()
        if client.has_collection(collection_name=collection_name):
            client.drop_collection(collection_name=collection_name)
        client.create_collection(collection_name=collection_name, schema=self._build_schema(), metric_type="IP")

    def _mock_insert_chunks(self, chunks: list[Chunk]) -> None:
        embeddings = embed_documents([chunk.content for chunk in chunks]) if chunks else []
        for chunk, embedding in zip(chunks, embeddings):
            payload = chunk.model_dump(mode="json")
            payload["embedding"] = embedding
            chunks_table.upsert(payload, "chunk_id")

    def _mock_insert_cases(self, cases: list[CaseSummary]) -> None:
        embeddings = embed_documents([case.summary for case in cases]) if cases else []
        for case, embedding in zip(cases, embeddings):
            payload = case.model_dump(mode="json")
            payload["embedding"] = embedding
            cases_table.upsert(payload, "case_id")

    def _mock_search_chunks(self, query_text: str, metadata_filter: dict[str, Any] | None, top_k: int) -> list[Evidence]:
        query_embedding = embed_query(query_text)
        hits: list[Evidence] = []
        for row in chunks_table.all():
            if metadata_filter and any(row.get(key) != value for key, value in metadata_filter.items()):
                continue
            score = _cosine(query_embedding, row.get("embedding", []))
            hits.append(Evidence(evidence_id=row["chunk_id"], source="milvus", content=row.get("content", ""), score=score, metadata=row))
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]

    def _mock_search_cases(self, query_text: str, top_k: int) -> list[Evidence]:
        query_embedding = embed_query(query_text)
        hits: list[Evidence] = []
        for row in cases_table.all():
            score = _cosine(query_embedding, row.get("embedding", []))
            hits.append(Evidence(evidence_id=row["case_id"], source="case_memory", content=row.get("summary", ""), score=score, metadata=row))
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]

    def insert_chunks(self, chunks: list[Chunk]) -> None:
        settings = self._settings()
        if _is_test_mode(settings):
            self._mock_insert_chunks(chunks)
            return
        self._ensure_collection(settings.milvus_collection)
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
            chunks_table.upsert(chunk, "chunk_id")
        if rows:
            try:
                self._client().upsert(collection_name=settings.milvus_collection, data=rows)
            except DataNotMatchException as exc:
                try:
                    self._validate_collection_schema(settings.milvus_collection)
                except MilvusSchemaMismatchError as mismatch:
                    self._handle_schema_mismatch(settings.milvus_collection, mismatch)
                    self._client().upsert(collection_name=settings.milvus_collection, data=rows)
                    return
                raise RuntimeError(
                    f"Milvus collection '{settings.milvus_collection}' rejected chunk rows: {exc}"
                ) from exc

    def insert_cases(self, cases: list[CaseSummary]) -> None:
        settings = self._settings()
        if _is_test_mode(settings):
            self._mock_insert_cases(cases)
            return
        self._ensure_collection(settings.milvus_case_collection)
        embeddings = embed_documents([case.summary for case in cases]) if cases else []
        rows = []
        for case, embedding in zip(cases, embeddings):
            rows.append(
                {
                    DEFAULT_ID_FIELD: case.case_id,
                    DEFAULT_VECTOR_FIELD: embedding,
                    "summary": case.summary,
                    "issue_type": case.issue_type,
                    "root_cause_chain_json": case.root_cause_chain_json,
                    "actions_json": case.actions_json,
                    "source_docs_json": case.source_docs_json,
                }
            )
            cases_table.upsert(case, "case_id")
        if rows:
            try:
                self._client().upsert(collection_name=settings.milvus_case_collection, data=rows)
            except DataNotMatchException as exc:
                try:
                    self._validate_collection_schema(settings.milvus_case_collection)
                except MilvusSchemaMismatchError as mismatch:
                    self._handle_schema_mismatch(settings.milvus_case_collection, mismatch)
                    self._client().upsert(collection_name=settings.milvus_case_collection, data=rows)
                    return
                raise RuntimeError(
                    f"Milvus collection '{settings.milvus_case_collection}' rejected case rows: {exc}"
                ) from exc

    def search(self, query_text: str, metadata_filter: dict[str, Any] | None = None, top_k: int = 5) -> list[Evidence]:
        settings = self._settings()
        metadata_filter = metadata_filter or {}
        if _is_test_mode(settings):
            return self._mock_search_chunks(query_text, metadata_filter, top_k)
        self._ensure_collection_loaded(settings.milvus_collection)
        query_embedding = embed_query(query_text)
        expression = _build_filter_expression(metadata_filter)
        try:
            raw_hits = self._client().search(
                collection_name=settings.milvus_collection,
                data=[query_embedding],
                filter=expression,
                limit=top_k,
                output_fields=DEFAULT_SEARCH_FIELDS,
            )
        except MilvusException as exc:
            if exc.code != 101 and "collection not loaded" not in str(exc).lower():
                raise
            logger.warning("Milvus collection '%s' was not loaded at search time; loading and retrying once.", settings.milvus_collection)
            self._load_collection(settings.milvus_collection)
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
                hits.append(Evidence(evidence_id=chunk_id or f"milvus_{len(hits)}", source="milvus", content=entity.get("content", metadata.get("content", "")), score=float(item.get("distance", 0.0)), metadata=metadata))
        return hits

    def search_cases(self, query_text: str, top_k: int = 5) -> list[Evidence]:
        settings = self._settings()
        if _is_test_mode(settings):
            return self._mock_search_cases(query_text, top_k)
        self._ensure_collection_loaded(settings.milvus_case_collection)
        query_embedding = embed_query(query_text)
        try:
            raw_hits = self._client().search(
                collection_name=settings.milvus_case_collection,
                data=[query_embedding],
                limit=top_k,
                output_fields=DEFAULT_SEARCH_FIELDS,
            )
        except MilvusException as exc:
            if exc.code != 101 and "collection not loaded" not in str(exc).lower():
                raise
            logger.warning(
                "Milvus collection '%s' was not loaded at case search time; loading and retrying once.",
                settings.milvus_case_collection,
            )
            self._load_collection(settings.milvus_case_collection)
            raw_hits = self._client().search(
                collection_name=settings.milvus_case_collection,
                data=[query_embedding],
                limit=top_k,
                output_fields=DEFAULT_SEARCH_FIELDS,
            )
        hits: list[Evidence] = []
        for group in raw_hits:
            for item in group:
                entity = item.get("entity", {})
                case_id = item.get(DEFAULT_ID_FIELD) or entity.get(DEFAULT_ID_FIELD)
                mysql_row = cases_table.get(case_id=case_id) if case_id else None
                metadata = dict(mysql_row or {})
                metadata.update(entity)
                hits.append(Evidence(evidence_id=case_id or f"case_{len(hits)}", source="case_memory", content=entity.get("summary", metadata.get("summary", "")), score=float(item.get("distance", 0.0)), metadata=metadata))
        return hits

    def ping(self) -> dict[str, Any]:
        settings = self._settings()
        if _is_test_mode(settings):
            return {"ok": True, "backend": "mock-milvus", "collections": [settings.milvus_collection, settings.milvus_case_collection]}
        try:
            self._ensure_collection_loaded(settings.milvus_collection)
            self._ensure_collection_loaded(settings.milvus_case_collection)
            self._client().list_collections()
            return {"ok": True, "backend": settings.milvus_uri, "collections": [settings.milvus_collection, settings.milvus_case_collection]}
        except Exception as exc:
            return {"ok": False, "backend": settings.milvus_uri, "collections": [settings.milvus_collection, settings.milvus_case_collection], "error": str(exc)}


milvus_store = MilvusStore()

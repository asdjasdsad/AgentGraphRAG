from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.core.db_milvus import MilvusStore, reset_milvus_clients
from app.core.db_mysql import RecordTable, reset_database_manager
from app.core.db_neo4j import GraphStore, reset_neo4j_drivers
from app.domain.enums import ChunkType, DocumentType
from app.domain.schemas import Chunk, Entity, Relation


def test_record_table_uses_sqlite_backend(monkeypatch, tmp_path) -> None:
    sqlite_path = tmp_path / "storage.db"
    settings = SimpleNamespace(mysql_url=f"sqlite:///{sqlite_path.as_posix()}")
    monkeypatch.setattr("app.core.db_mysql.get_settings", lambda: settings)
    reset_database_manager()

    table = RecordTable("documents", "document_id")
    table.upsert({"document_id": "doc_001", "file_name": "demo.pdf"}, "document_id")

    assert table.get(document_id="doc_001")["file_name"] == "demo.pdf"
    assert table.ping()["ok"] is True


def test_milvus_store_calls_real_client(monkeypatch) -> None:
    requests: list[dict] = []

    class FakeSchema:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.fields: list[dict] = []

        def add_field(self, name: str, dtype, **kwargs) -> None:
            self.fields.append({"name": name, "dtype": dtype, **kwargs})

    class FakeMilvusClient:
        def __init__(self, **kwargs) -> None:
            requests.append({"kind": "init", "kwargs": kwargs})

        def has_collection(self, collection_name: str) -> bool:
            requests.append({"kind": "has_collection", "collection_name": collection_name})
            return False

        def create_schema(self, **kwargs):
            schema = FakeSchema(**kwargs)
            requests.append({"kind": "create_schema", "kwargs": kwargs, "schema": schema})
            return schema

        def create_collection(self, **kwargs) -> None:
            requests.append({"kind": "create_collection", "kwargs": kwargs})

        def upsert(self, **kwargs) -> None:
            requests.append({"kind": "upsert", "kwargs": kwargs})

    settings = SimpleNamespace(
        app_env="dev",
        milvus_uri="http://127.0.0.1:19530",
        milvus_token="",
        milvus_database="default",
        milvus_collection="chunks",
        embedding_dimensions=256,
    )
    monkeypatch.setattr("app.core.db_milvus.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.db_milvus.MilvusClient", FakeMilvusClient)
    monkeypatch.setattr("app.core.db_milvus.embed_documents", lambda texts: [[1.0, 0.0, 0.0] for _ in texts])
    monkeypatch.setattr("app.core.db_milvus.chunks_table.upsert", lambda payload, key: payload)
    reset_milvus_clients()

    store = MilvusStore()
    store.insert_chunks(
        [
            Chunk(
                chunk_id="chunk_001",
                document_id="doc_001",
                doc_type=DocumentType.ANALYSIS_REPORT,
                chunk_type=ChunkType.CAUSE_ANALYSIS,
                section_path="3.原因分析",
                content="液压泵泄漏的原因是密封圈老化",
            )
        ]
    )

    schema_request = next(item for item in requests if item["kind"] == "create_schema")
    create_request = next(item for item in requests if item["kind"] == "create_collection")
    upsert_request = next(item for item in requests if item["kind"] == "upsert")
    assert schema_request["kwargs"] == {"auto_id": False, "enable_dynamic_field": True}
    assert create_request["kwargs"]["collection_name"] == "chunks"
    assert create_request["kwargs"]["schema"].fields[0]["name"] == "id"
    assert create_request["kwargs"]["schema"].fields[0]["is_primary"] is True
    assert create_request["kwargs"]["schema"].fields[1]["dim"] == 256
    assert upsert_request["kwargs"]["data"][0]["id"] == "chunk_001"


def test_milvus_store_loads_collection_before_search(monkeypatch) -> None:
    requests: list[dict] = []

    class FakeMilvusClient:
        def __init__(self, **kwargs) -> None:
            requests.append({"kind": "init", "kwargs": kwargs})

        def has_collection(self, collection_name: str) -> bool:
            requests.append({"kind": "has_collection", "collection_name": collection_name})
            return True

        def load_collection(self, collection_name: str) -> None:
            requests.append({"kind": "load_collection", "collection_name": collection_name})

        def search(self, **kwargs):
            requests.append({"kind": "search", "kwargs": kwargs})
            return [[{"id": "chunk_001", "distance": 0.9, "entity": {"id": "chunk_001", "content": "match"}}]]

    settings = SimpleNamespace(
        app_env="dev",
        milvus_uri="http://127.0.0.1:19530",
        milvus_token="",
        milvus_database="default",
        milvus_collection="chunks",
        milvus_case_collection="cases",
        embedding_dimensions=256,
    )
    monkeypatch.setattr("app.core.db_milvus.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.db_milvus.MilvusClient", FakeMilvusClient)
    monkeypatch.setattr("app.core.db_milvus.embed_query", lambda text: [1.0, 0.0, 0.0])
    monkeypatch.setattr("app.core.db_milvus.chunks_table.get", lambda **kwargs: {"chunk_id": kwargs.get("chunk_id"), "content": "match"})
    reset_milvus_clients()

    store = MilvusStore()
    hits = store.search("demo question", {"document_id": "doc_001"}, 3)

    load_request = next(item for item in requests if item["kind"] == "load_collection")
    search_request = next(item for item in requests if item["kind"] == "search")
    assert load_request["collection_name"] == "chunks"
    assert search_request["kwargs"]["collection_name"] == "chunks"
    assert search_request["kwargs"]["filter"] == 'document_id == "doc_001"'
    assert hits[0].evidence_id == "chunk_001"


def test_graph_store_calls_neo4j_driver(monkeypatch, tmp_path) -> None:
    run_calls: list[dict] = []

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def run(self, query: str, **params):
            run_calls.append({"query": query, "params": params})
            return []

    class FakeDriver:
        def session(self, database: str):
            run_calls.append({"database": database})
            return FakeSession()

    settings = SimpleNamespace(
        app_env="dev",
        neo4j_uri="bolt://127.0.0.1:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        neo4j_database="neo4j",
        store_dir=tmp_path,
    )
    monkeypatch.setattr("app.core.db_neo4j.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.db_neo4j.GraphDatabase.driver", lambda uri, auth: FakeDriver())
    reset_neo4j_drivers()

    store = GraphStore()
    store.upsert_graph(
        [Entity(name="液压泵", type="Component"), Entity(name="泄漏", type="Phenomenon")],
        [Relation(source="液压泵", type="CAUSES", target="泄漏")],
    )

    assert any("MERGE (n:Component" in item["query"] for item in run_calls if "query" in item)
    assert any("MATCH (a:Component" in item["query"] and "MERGE (a)-[r:CAUSES]->(b)" in item["query"] for item in run_calls if "query" in item)

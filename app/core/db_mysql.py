from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import MetaData, Table, Column, String, Text, create_engine, select, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings


TABLE_SPECS = {
    "documents": "document_id",
    "ingestion_jobs": "job_id",
    "chunks": "chunk_id",
    "cases": "case_id",
    "audit_logs": "trace_id",
    "risk_rules": "rule_id",
}


def _sqlite_path(mysql_url: str) -> Path | None:
    if not mysql_url.startswith("sqlite:///"):
        return None
    raw_path = mysql_url.removeprefix("sqlite:///")
    return Path(raw_path).resolve()


@lru_cache(maxsize=4)
def get_engine(mysql_url: str) -> Engine:
    sqlite_path = _sqlite_path(mysql_url)
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {"future": True}
    if sqlite_path:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args["check_same_thread"] = False
        engine_kwargs["connect_args"] = connect_args
    else:
        engine_kwargs["pool_pre_ping"] = True
    return create_engine(mysql_url, **engine_kwargs)


@lru_cache(maxsize=4)
def get_metadata(mysql_url: str) -> MetaData:
    metadata = MetaData()
    for table_name, key_name in TABLE_SPECS.items():
        Table(
            table_name,
            metadata,
            Column(key_name, String(191), primary_key=True),
            Column("payload", Text, nullable=False),
        )
    metadata.create_all(get_engine(mysql_url))
    return metadata


def reset_database_manager() -> None:
    get_metadata.cache_clear()
    get_engine.cache_clear()


class RecordTable:
    def __init__(self, table_name: str, key_name: str):
        self.table_name = table_name
        self.key_name = key_name

    def _engine(self) -> Engine:
        return get_engine(get_settings().mysql_url)

    def _table(self) -> Table:
        mysql_url = get_settings().mysql_url
        metadata = get_metadata(mysql_url)
        return metadata.tables[self.table_name]

    def _serialize(self, item: BaseModel | dict[str, Any]) -> dict[str, Any]:
        return item.model_dump(mode="json") if isinstance(item, BaseModel) else dict(item)

    def _deserialize(self, raw_payload: str) -> dict[str, Any]:
        return json.loads(raw_payload)

    def ping(self) -> dict[str, Any]:
        try:
            with self._engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"ok": True, "backend": get_settings().mysql_url}
        except Exception as exc:  # pragma: no cover - exercised in app runtime
            return {"ok": False, "backend": get_settings().mysql_url, "error": str(exc)}

    def all(self) -> list[dict[str, Any]]:
        table = self._table()
        with self._engine().connect() as conn:
            rows = conn.execute(select(table.c.payload)).all()
        return [self._deserialize(row[0]) for row in rows]

    def upsert(self, item: BaseModel | dict[str, Any], key: str) -> dict[str, Any]:
        if key != self.key_name:
            raise ValueError(f"{self.table_name} expects key {self.key_name}, got {key}")
        payload = self._serialize(item)
        key_value = payload.get(self.key_name)
        if not key_value:
            raise ValueError(f"Missing primary key {self.key_name} for table {self.table_name}")

        table = self._table()
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self._engine().begin() as conn:
            existing = conn.execute(select(table.c[self.key_name]).where(table.c[self.key_name] == key_value)).first()
            if existing:
                conn.execute(
                    table.update().where(table.c[self.key_name] == key_value).values(payload=payload_json)
                )
            else:
                conn.execute(
                    table.insert().values(
                        {
                            self.key_name: key_value,
                            "payload": payload_json,
                        }
                    )
                )
        return payload

    def filter(self, **conditions: Any) -> list[dict[str, Any]]:
        rows = self.all()
        return [row for row in rows if all(row.get(field) == value for field, value in conditions.items())]

    def get(self, **conditions: Any) -> dict[str, Any] | None:
        for row in self.filter(**conditions):
            return row
        return None

    def ids(self) -> Iterable[str]:
        table = self._table()
        with self._engine().connect() as conn:
            rows = conn.execute(select(table.c[self.key_name])).all()
        return [row[0] for row in rows]


documents_table = RecordTable("documents", "document_id")
jobs_table = RecordTable("ingestion_jobs", "job_id")
chunks_table = RecordTable("chunks", "chunk_id")
cases_table = RecordTable("cases", "case_id")
audit_logs_table = RecordTable("audit_logs", "trace_id")
risk_rules_table = RecordTable("risk_rules", "rule_id")

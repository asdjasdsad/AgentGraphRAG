from __future__ import annotations

from app.core.db_neo4j import graph_store


def query_graph(entity_names: list[str], relation_type: str | None = None) -> list[dict]:
    return [item.model_dump(mode="json") for item in graph_store.query(entity_names, relation_type=relation_type)]

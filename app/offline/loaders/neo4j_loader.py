from __future__ import annotations

from app.core.db_neo4j import graph_store
from app.domain.schemas import Entity, Relation


def load_graph_data(entities: list[dict], relations: list[dict]) -> None:
    graph_store.upsert_graph(
        [Entity(**entity) for entity in entities],
        [Relation(**relation) for relation in relations],
    )

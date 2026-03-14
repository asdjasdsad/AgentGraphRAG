from __future__ import annotations

from app.core.db_neo4j import graph_store


def retrieve_graph_evidence(state: dict) -> dict:
    entities = state.get("entities", [])
    relation_type = state.get("relation_type")
    hits = graph_store.query(entities, relation_type=relation_type, max_hops=2)
    return {"graph_hits": hits, "retrieved_evidence": hits}

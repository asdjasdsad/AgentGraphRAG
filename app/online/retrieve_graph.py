from __future__ import annotations

from app.core.db_neo4j import graph_store


def retrieve_graph_evidence(state: dict) -> dict:
    query_plan = state.get("query_plan")
    max_hops = query_plan.get("max_hops", 2) if isinstance(query_plan, dict) else (query_plan.max_hops if query_plan else 2)
    entities = state.get("entities", [])
    relation_type = state.get("relation_type") or None
    hits = graph_store.query(entities, relation_type=relation_type, max_hops=max_hops)
    return {"graph_hits": hits, "retrieved_evidence": hits}

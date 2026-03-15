from __future__ import annotations

from app.core.config import get_settings
from app.domain.enums import RetrievalStrategy
from app.domain.schemas import QueryPlan


def _build_metadata_filter(constraints: list[str]) -> dict[str, str]:
    filters: dict[str, str] = {}
    for item in constraints:
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        if key == "issue_id":
            filters["issue_id"] = value
    return filters


def build_query_plan(state: dict) -> QueryPlan:
    settings = get_settings()
    strategy = state["retrieval_strategy"]
    question = state["question"]
    entities = state.get("entities", [])
    relation_type = state.get("relation_type") or "CAUSES"
    question_type = state.get("question_type") or "knowledge_search"
    constraints = state.get("constraints", [])
    metadata_filter = _build_metadata_filter(constraints)
    top_k = 10 if question_type == "case_lookup" else 6 if question_type == "verification_check" else 8
    max_hops = settings.max_graph_hops if state.get("need_multihop") else min(2, settings.max_graph_hops)
    if strategy in {RetrievalStrategy.GRAPH, RetrievalStrategy.HYBRID}:
        return QueryPlan(
            retrieval_strategy=strategy,
            query_text=question,
            cypher_query=(
                "MATCH path = (a)-[r*1..$max_hops]-(b) "
                "WHERE (size($entities) = 0 OR a.name IN $entities OR b.name IN $entities) "
                "RETURN path LIMIT $limit"
            ),
            cypher_params={"entities": entities, "limit": top_k + 2, "relation_type": relation_type, "max_hops": max_hops},
            metadata_filter=metadata_filter,
            top_k=top_k,
            max_hops=max_hops,
        )
    return QueryPlan(retrieval_strategy=strategy, query_text=question, metadata_filter=metadata_filter, top_k=top_k, max_hops=max_hops)

from __future__ import annotations

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
    strategy = state["retrieval_strategy"]
    question = state["question"]
    entities = state.get("entities", [])
    relation_type = state.get("relation_type") or "CAUSES"
    question_type = state.get("question_type") or "knowledge_search"
    constraints = state.get("constraints", [])
    metadata_filter = _build_metadata_filter(constraints)

    top_k = 8
    if question_type == "case_lookup":
        top_k = 10
    elif question_type == "verification_check":
        top_k = 6

    if strategy == RetrievalStrategy.GRAPH:
        return QueryPlan(
            retrieval_strategy=strategy,
            query_text=question,
            cypher_query=(
                "MATCH path = (a)-[r]->(b) "
                "WHERE (a.name IN $entities OR b.name IN $entities) "
                "AND ($relation_type = '' OR type(r) = $relation_type) "
                "RETURN path LIMIT $limit"
            ),
            cypher_params={"entities": entities, "limit": 10, "relation_type": relation_type},
            metadata_filter=metadata_filter,
            top_k=top_k,
        )
    if strategy == RetrievalStrategy.HYBRID:
        return QueryPlan(
            retrieval_strategy=strategy,
            query_text=question,
            cypher_query=(
                "MATCH path = (a)-[r]->(b) "
                "WHERE (a.name IN $entities OR b.name IN $entities) "
                "AND ($relation_type = '' OR type(r) = $relation_type) "
                "RETURN path LIMIT $limit"
            ),
            cypher_params={"entities": entities, "limit": 12, "relation_type": relation_type},
            metadata_filter=metadata_filter,
            top_k=max(top_k, 8),
        )
    return QueryPlan(
        retrieval_strategy=strategy,
        query_text=question,
        metadata_filter=metadata_filter,
        top_k=top_k,
    )

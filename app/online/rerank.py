from __future__ import annotations

from app.domain.schemas import Evidence


DOC_TYPE_BONUS = {
    "analysis_report": 0.12,
    "action_report": 0.1,
    "issue_record": 0.08,
}


def _as_evidence(item: Evidence | dict) -> Evidence:
    return item if isinstance(item, Evidence) else Evidence(**item)


def rerank_evidence(state: dict) -> dict:
    entities = set(state.get("entities", []))
    relation_type = state.get("relation_type") or ""
    metadata_filter = (state.get("query_plan") or {}).get("metadata_filter", {}) if isinstance(state.get("query_plan"), dict) else {}

    reranked: list[Evidence] = []
    reasoning_path: list[dict] = []
    for evidence in state.get("retrieved_evidence", []):
        item = _as_evidence(evidence)
        content = item.content
        metadata = item.metadata or {}
        semantic_score = item.score
        entity_coverage = sum(0.12 for entity in entities if entity in content)
        relation_bonus = 0.18 if relation_type and relation_type in content else 0.0
        graph_bonus = 0.12 if item.source == "neo4j" else 0.0
        doc_type_bonus = DOC_TYPE_BONUS.get(str(metadata.get("doc_type", "")), 0.0)
        exact_issue_bonus = 0.2 if metadata_filter.get("issue_id") and metadata_filter.get("issue_id") == metadata.get("issue_id") else 0.0
        final_score = semantic_score + entity_coverage + relation_bonus + graph_bonus + doc_type_bonus + exact_issue_bonus
        item.score = final_score
        reranked.append(item)
        reasoning_path.append(
            {
                "evidence_id": item.evidence_id,
                "source": item.source,
                "semantic_score": round(semantic_score, 4),
                "entity_coverage": round(entity_coverage, 4),
                "relation_bonus": round(relation_bonus, 4),
                "graph_bonus": round(graph_bonus, 4),
                "doc_type_bonus": round(doc_type_bonus, 4),
                "exact_issue_bonus": round(exact_issue_bonus, 4),
                "score": round(final_score, 4),
            }
        )

    reranked.sort(key=lambda item: item.score, reverse=True)
    reasoning_path.sort(key=lambda item: item["score"], reverse=True)
    for index, item in enumerate(reasoning_path[:5], start=1):
        item["step"] = index
    return {"reranked_evidence": reranked, "reasoning_path": reasoning_path[:5]}

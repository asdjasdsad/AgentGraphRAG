from __future__ import annotations

from app.domain.schemas import Evidence


DOC_TYPE_BONUS = {"analysis_report": 0.12, "action_report": 0.10, "issue_record": 0.08}
SOURCE_BONUS = {"neo4j": 0.12, "case_memory": 0.08, "milvus": 0.0}


def _as_evidence(item: Evidence | dict) -> Evidence:
    return item if isinstance(item, Evidence) else Evidence(**item)


def rerank_evidence(state: dict) -> dict:
    entities = set(state.get("entities", []))
    relation_type = state.get("relation_type") or ""
    query_plan = state.get("query_plan")
    metadata_filter = query_plan.get("metadata_filter", {}) if isinstance(query_plan, dict) else (query_plan.metadata_filter if query_plan else {})
    reranked: list[Evidence] = []
    reasoning_path: list[dict] = []
    for evidence in state.get("retrieved_evidence", []):
        item = _as_evidence(evidence)
        content = item.content
        metadata = item.metadata or {}
        semantic_score = item.score
        entity_coverage = sum(0.12 for entity in entities if entity in content)
        relation_bonus = 0.16 if relation_type and relation_type in content else 0.0
        source_bonus = SOURCE_BONUS.get(item.source, 0.0)
        doc_type_bonus = DOC_TYPE_BONUS.get(str(metadata.get("doc_type", "")), 0.0)
        exact_issue_bonus = 0.2 if metadata_filter.get("issue_id") and metadata_filter.get("issue_id") == metadata.get("issue_id") else 0.0
        final_score = semantic_score + entity_coverage + relation_bonus + source_bonus + doc_type_bonus + exact_issue_bonus
        item.score = final_score
        reranked.append(item)
        reasoning_path.append({
            "evidence_id": item.evidence_id,
            "source": item.source,
            "score": round(final_score, 4),
            "summary": content[:180],
        })
    reranked.sort(key=lambda item: item.score, reverse=True)
    reasoning_path.sort(key=lambda item: item["score"], reverse=True)
    for index, item in enumerate(reasoning_path[:5], start=1):
        item["step"] = index
    return {"reranked_evidence": reranked[:10], "reasoning_path": reasoning_path[:5]}

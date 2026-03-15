from __future__ import annotations

from app.core.db_milvus import milvus_store


def retrieve_vector_evidence(state: dict) -> dict:
    plan = state["query_plan"]
    query_text = plan["query_text"] if isinstance(plan, dict) else plan.query_text
    metadata_filter = plan["metadata_filter"] if isinstance(plan, dict) else plan.metadata_filter
    top_k = plan["top_k"] if isinstance(plan, dict) else plan.top_k
    hits = milvus_store.search(query_text, metadata_filter, top_k)
    return {"vector_hits": hits, "retrieved_evidence": hits}

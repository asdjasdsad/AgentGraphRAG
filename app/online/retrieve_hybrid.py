from __future__ import annotations

from app.core.db_milvus import milvus_store
from app.online.retrieve_graph import retrieve_graph_evidence
from app.online.retrieve_vector import retrieve_vector_evidence


def retrieve_hybrid_evidence(state: dict) -> dict:
    query_plan = state.get("query_plan")
    query_text = query_plan.get("query_text") if isinstance(query_plan, dict) else query_plan.query_text
    top_k = query_plan.get("top_k", 5) if isinstance(query_plan, dict) else query_plan.top_k
    vector_data = retrieve_vector_evidence(state)
    graph_data = retrieve_graph_evidence(state)
    case_hits = milvus_store.search_cases(query_text, top_k=max(3, min(top_k, 5)))
    evidence = list(vector_data["vector_hits"]) + list(graph_data["graph_hits"]) + list(case_hits)
    return {
        "vector_hits": vector_data["vector_hits"],
        "graph_hits": graph_data["graph_hits"],
        "case_hits": case_hits,
        "retrieved_evidence": evidence,
    }

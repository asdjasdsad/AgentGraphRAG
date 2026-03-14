from __future__ import annotations

from app.online.retrieve_graph import retrieve_graph_evidence
from app.online.retrieve_vector import retrieve_vector_evidence


def retrieve_hybrid_evidence(state: dict) -> dict:
    vector_data = retrieve_vector_evidence(state)
    graph_data = retrieve_graph_evidence(state)
    evidence = list(vector_data["vector_hits"]) + list(graph_data["graph_hits"])
    return {
        "vector_hits": vector_data["vector_hits"],
        "graph_hits": graph_data["graph_hits"],
        "retrieved_evidence": evidence,
    }

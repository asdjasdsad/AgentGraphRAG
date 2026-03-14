from __future__ import annotations

from app.mcp.resources_schema import load_schema_resource
from app.mcp.tools_cases import search_case_memory
from app.mcp.tools_graph import query_graph
from app.mcp.tools_vector import search_vector_evidence


def get_tools_manifest() -> dict:
    return {
        "tools": ["search_vector_evidence", "query_graph", "search_case_memory"],
        "resources": load_schema_resource(),
    }


__all__ = ["search_vector_evidence", "query_graph", "search_case_memory", "get_tools_manifest"]

from __future__ import annotations

from app.memory.case_memory import case_memory


def search_case_memory(query: str) -> list[dict]:
    return case_memory.search(query)

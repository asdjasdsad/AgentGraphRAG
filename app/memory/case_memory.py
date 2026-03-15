from __future__ import annotations

from app.core.db_milvus import milvus_store
from app.core.db_mysql import cases_table


class CaseMemory:
    def search(self, query: str, limit: int = 5) -> list[dict]:
        vector_hits = milvus_store.search_cases(query, top_k=limit)
        if vector_hits:
            return [item.model_dump(mode="json") for item in vector_hits]
        rows = []
        for row in cases_table.all():
            if query in row.get("summary", "") or query in row.get("issue_type", ""):
                rows.append(row)
        return rows[:limit]

    def get(self, case_id: str) -> dict | None:
        return cases_table.get(case_id=case_id)


case_memory = CaseMemory()

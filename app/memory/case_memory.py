from __future__ import annotations

from app.core.db_mysql import cases_table


class CaseMemory:
    def search(self, query: str) -> list[dict]:
        rows = cases_table.all()
        return [row for row in rows if query in row.get("summary", "") or query in row.get("issue_type", "")]

    def get(self, case_id: str) -> dict | None:
        return cases_table.get(case_id=case_id)


case_memory = CaseMemory()

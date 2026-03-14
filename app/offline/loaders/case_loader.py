from __future__ import annotations

from app.core.db_mysql import cases_table
from app.domain.schemas import CaseSummary


def persist_case_memory(case_summary: CaseSummary) -> dict:
    return cases_table.upsert(case_summary, "case_id")

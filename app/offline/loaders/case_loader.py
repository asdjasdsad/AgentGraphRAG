from __future__ import annotations

from app.core.db_milvus import milvus_store
from app.core.db_mysql import cases_table
from app.domain.schemas import CaseSummary


def persist_case_memory(case_summary: CaseSummary) -> dict:
    cases_table.upsert(case_summary, "case_id")
    milvus_store.insert_cases([case_summary])
    return case_summary.model_dump(mode="json")

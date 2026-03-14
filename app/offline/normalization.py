from __future__ import annotations

from app.domain.schemas import StructuredRecord
from app.utils.alias_map import normalize_alias
from app.utils.text_utils import clean_text


def normalize_record(record: dict) -> StructuredRecord:
    phenomenon = normalize_alias(clean_text(record.get("phenomenon", "")))
    components = [normalize_alias(clean_text(item)) for item in record.get("component", []) if clean_text(item)]
    causes = [normalize_alias(clean_text(item)) for item in record.get("cause", []) if clean_text(item)]
    actions = [normalize_alias(clean_text(item)) for item in record.get("action", []) if clean_text(item)]
    return StructuredRecord(
        issue_id=clean_text(record.get("issue_id", "")),
        phenomenon=phenomenon,
        component=components,
        cause=causes,
        action=actions,
        source_type=record.get("source_type", "structured"),
        source_system=record.get("source_system", "api"),
        load_batch_id=record.get("load_batch_id"),
    )

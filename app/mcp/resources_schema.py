from __future__ import annotations

from app.domain.ontology import ENTITY_TYPES, RELATION_TYPES


def load_schema_resource() -> dict:
    return {"entities": ENTITY_TYPES, "relations": RELATION_TYPES}

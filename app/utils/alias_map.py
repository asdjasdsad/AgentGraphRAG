from app.domain.ontology import ENTITY_ALIASES


def normalize_alias(value: str) -> str:
    normalized = value.strip()
    return ENTITY_ALIASES.get(normalized, normalized)

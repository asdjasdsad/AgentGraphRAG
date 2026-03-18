from __future__ import annotations

import re

from cypher_agent_ft.common.types import GraphSchema, ModelOutput


LABEL_RE = re.compile(r"\([A-Za-z_][A-Za-z0-9_]*:([A-Za-z_][A-Za-z0-9_]*)")
REL_RE = re.compile(r"\[:([A-Za-z_][A-Za-z0-9_]*)")
PROP_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)")


def check_schema_compliance(schema: GraphSchema, output: ModelOutput) -> tuple[bool, list[str]]:
    errors: list[str] = []
    allowed_labels = set(schema.node_types)
    allowed_relations = {item.type for item in schema.relation_types}
    allowed_props = {prop for props in schema.property_keys.values() for prop in props}
    labels = set(LABEL_RE.findall(output.cypher))
    relations = set(REL_RE.findall(output.cypher))
    for label in labels:
        if label not in allowed_labels:
            errors.append(f"unknown label: {label}")
    for relation in relations:
        if relation not in allowed_relations:
            errors.append(f"unknown relation: {relation}")
    for _, prop in PROP_RE.findall(output.cypher):
        if prop not in allowed_props:
            errors.append(f"unknown property: {prop}")
    return not errors, errors

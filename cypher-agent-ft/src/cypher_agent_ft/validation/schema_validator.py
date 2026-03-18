from __future__ import annotations

from cypher_agent_ft.common.types import GraphSchema, ModelOutput
from cypher_agent_ft.schema.checker import check_schema_compliance


def validate_against_schema(schema: GraphSchema, output: ModelOutput) -> tuple[bool, list[str]]:
    return check_schema_compliance(schema, output)

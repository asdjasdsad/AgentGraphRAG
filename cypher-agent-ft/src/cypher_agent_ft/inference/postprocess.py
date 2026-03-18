from __future__ import annotations

from cypher_agent_ft.common.types import ModelOutput


def normalize_output(output: ModelOutput) -> ModelOutput:
    output.query_plan.required_relations = list(dict.fromkeys(output.query_plan.required_relations))
    return output

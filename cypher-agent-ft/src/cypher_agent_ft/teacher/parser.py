from __future__ import annotations

from cypher_agent_ft.common.types import ModelOutput


def parse_model_output(payload: dict) -> ModelOutput:
    return ModelOutput.model_validate(payload)

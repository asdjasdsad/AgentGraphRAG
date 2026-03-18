from __future__ import annotations

from cypher_agent_ft.common.types import ModelOutput


def validate_model_output(payload: dict | ModelOutput) -> tuple[bool, list[str], ModelOutput | None]:
    try:
        parsed = payload if isinstance(payload, ModelOutput) else ModelOutput.model_validate(payload)
        return True, [], parsed
    except Exception as exc:
        return False, [str(exc)], None

from __future__ import annotations

from pathlib import Path

from cypher_agent_ft.common.io import load_config
from cypher_agent_ft.common.types import GraphSchema


def load_schema(path: Path) -> GraphSchema:
    return GraphSchema.model_validate(load_config(path))

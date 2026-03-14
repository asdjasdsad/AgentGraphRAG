from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPTS_DIR = Path(__file__).resolve().parent
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def _normalize_name(name: str) -> str:
    return name if name.endswith(".txt") else f"{name}.txt"


@lru_cache(maxsize=32)
def get_prompt(name: str) -> str:
    path = PROMPTS_DIR / _normalize_name(name)
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **values: Any) -> str:
    template = get_prompt(name)

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = values.get(key, "")
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return "\n".join(f"- {item}" for item in value) if value else "- (empty)"
        if isinstance(value, dict):
            return "\n".join(f"- {sub_key}: {sub_value}" for sub_key, sub_value in value.items()) if value else "- (empty)"
        return str(value)

    return PLACEHOLDER_PATTERN.sub(replace, template)

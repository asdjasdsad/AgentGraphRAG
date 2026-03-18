from __future__ import annotations

from pathlib import Path
from typing import Any

from app.prompts.registry import PROMPT_CATALOG, get_prompt, render_prompt


def list_prompts() -> list[dict[str, Any]]:
    prompts_dir = Path(__file__).resolve().parent
    payload: list[dict[str, Any]] = []
    for name, meta in PROMPT_CATALOG.items():
        file_name = meta["file"]
        payload.append(
            {
                "name": name,
                "file": file_name,
                "version": meta["version"],
                "purpose": meta["purpose"],
                "path": str(prompts_dir / file_name),
            }
        )
    return payload


__all__ = ["PROMPT_CATALOG", "get_prompt", "render_prompt", "list_prompts"]

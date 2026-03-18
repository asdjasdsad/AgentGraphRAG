from __future__ import annotations

from fastapi import APIRouter

from app.prompts import list_prompts


router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("")
def prompt_registry() -> list[dict]:
    return list_prompts()

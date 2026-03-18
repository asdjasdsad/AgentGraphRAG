from __future__ import annotations

import json

from cypher_agent_ft.common.types import PromptInput


def build_teacher_prompt(prompt: PromptInput) -> str:
    return (
        "根据结构化图查询任务输入生成 query_plan 和 Cypher，必须满足 schema 和查询约束。"
        "只输出 JSON，字段必须是 query_plan 和 cypher。\n\n"
        + json.dumps(prompt.model_dump(mode="json"), ensure_ascii=False, indent=2)
    )

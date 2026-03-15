from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPTS_DIR = Path(__file__).resolve().parent
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
PROMPT_CATALOG: dict[str, dict[str, str]] = {
    "classify_doc": {
        "file": "classify_doc.txt",
        "version": "v1.0.0",
        "purpose": "根据文件名、首页文本和标题判断文档类型。",
    },
    "extract_entities": {
        "file": "extract_entities.txt",
        "version": "v1.0.0",
        "purpose": "抽取组件、现象、原因、措施及其关系。",
    },
    "parse_question": {
        "file": "parse_question.txt",
        "version": "v1.1.0",
        "purpose": "解析问句中的实体、关系、约束和多跳意图。",
    },
    "route_retrieval": {
        "file": "route_retrieval.txt",
        "version": "v1.1.0",
        "purpose": "在 graph、vector、hybrid 间选择检索策略。",
    },
    "safe_answer": {
        "file": "safe_answer.txt",
        "version": "v1.1.0",
        "purpose": "基于证据和风险等级生成保守、可追溯的回答。",
    },
    "verify_evidence": {
        "file": "verify_evidence.txt",
        "version": "v1.1.0",
        "purpose": "检查证据充分性、冲突和降级策略。",
    },
}


def _normalize_name(name: str) -> str:
    if name in PROMPT_CATALOG:
        return PROMPT_CATALOG[name]["file"]
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

from __future__ import annotations

import re
from typing import Any

from app.prompts import render_prompt


COMPONENT_HINTS = (
    "液压泵",
    "密封圈",
    "阀门",
    "轴承",
    "传感器",
    "作动筒",
    "管路",
    "滤芯",
    "接头",
    "泵体",
)
PHENOMENON_HINTS = (
    "泄漏",
    "渗漏",
    "异响",
    "裂纹",
    "过热",
    "失效",
    "松动",
    "卡滞",
    "磨损",
    "振动",
)
CAUSE_HINTS = (
    "老化",
    "磨损",
    "腐蚀",
    "装配不良",
    "污染",
    "疲劳",
    "间隙过大",
    "密封失效",
    "超温",
)
ACTION_HINTS = (
    "更换",
    "维修",
    "整改",
    "校准",
    "复测",
    "清洗",
    "润滑",
    "加固",
    "排故",
)
CAUSE_KEYWORDS = ("原因", "根因", "为什么", "诱因", "导致", "追溯")
ACTION_KEYWORDS = ("措施", "建议", "整改", "维修", "怎么处理", "如何处理", "修复")
CASE_KEYWORDS = ("案例", "历史", "类似", "同类", "先例", "复现")
VERIFY_KEYWORDS = ("是否", "有没有", "闭环", "验证", "确认", "核验")
MULTIHOP_KEYWORDS = ("根因链", "路径", "链路", "追溯", "多跳", "影响链")
CONSTRAINT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"Q\d{4}-\d{3,}", "issue_id"),
    (r"(?:最近|近三个月|近半年|近一年)", "time_window"),
    (r"(?:A320|A330|B737|B787|ARJ21|C919)", "aircraft_model"),
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _extract_hints(question: str, hints: tuple[str, ...]) -> list[str]:
    return [hint for hint in hints if hint in question]


def _extract_constraints(question: str) -> list[str]:
    constraints: list[str] = []
    for pattern, label in CONSTRAINT_PATTERNS:
        for match in re.findall(pattern, question):
            constraints.append(f"{label}:{match}")
    if "责任单位" in question:
        constraints.append("dimension:responsible_org")
    if "页码" in question or "哪一页" in question:
        constraints.append("need_page_reference")
    return _dedupe(constraints)


def _build_analysis_notes(
    *,
    entities: list[str],
    question_type: str,
    relation_type: str,
    constraints: list[str],
    need_multihop: bool,
    retrieval_strategy: str,
) -> list[str]:
    notes = [f"识别为 {question_type} 问题，推荐 {retrieval_strategy} 检索。"]
    if entities:
        notes.append(f"识别到关键实体：{', '.join(entities)}。")
    else:
        notes.append("没有识别出强实体，后续更依赖语义检索补证据。")
    if relation_type:
        notes.append(f"关系意图聚焦在 {relation_type}。")
    if constraints:
        notes.append(f"额外约束：{'; '.join(constraints)}。")
    if need_multihop:
        notes.append("问题存在多跳追溯意图，需要图关系和文本证据协同。")
    return notes


def analyze_question(question: str, allowed_scope: list[str] | None = None) -> dict[str, Any]:
    entities = _dedupe(
        _extract_hints(question, COMPONENT_HINTS)
        + _extract_hints(question, PHENOMENON_HINTS)
        + _extract_hints(question, CAUSE_HINTS)
        + _extract_hints(question, ACTION_HINTS)
        + re.findall(r"Q\d{4}-\d{3,}", question)
    )
    constraints = _extract_constraints(question)

    has_cause_intent = any(keyword in question for keyword in CAUSE_KEYWORDS)
    has_action_intent = any(keyword in question for keyword in ACTION_KEYWORDS)
    has_case_intent = any(keyword in question for keyword in CASE_KEYWORDS)
    has_verify_intent = any(keyword in question for keyword in VERIFY_KEYWORDS)
    need_multihop = any(keyword in question for keyword in MULTIHOP_KEYWORDS) or (has_cause_intent and has_action_intent)

    if has_case_intent:
        question_type = "case_lookup"
    elif has_verify_intent and not has_action_intent and not has_cause_intent:
        question_type = "verification_check"
    elif has_action_intent and not has_cause_intent:
        question_type = "action_recommendation"
    elif has_cause_intent:
        question_type = "cause_trace"
    else:
        question_type = "knowledge_search"

    if has_cause_intent:
        relation_type = "CAUSES"
    elif has_action_intent:
        relation_type = "MITIGATES"
    elif any(component in question for component in COMPONENT_HINTS):
        relation_type = "INVOLVES_COMPONENT"
    else:
        relation_type = ""

    if need_multihop or (entities and relation_type and has_case_intent):
        retrieval_strategy = "hybrid"
    elif entities and relation_type:
        retrieval_strategy = "graph"
    else:
        retrieval_strategy = "vector"

    analysis_notes = _build_analysis_notes(
        entities=entities,
        question_type=question_type,
        relation_type=relation_type,
        constraints=constraints,
        need_multihop=need_multihop,
        retrieval_strategy=retrieval_strategy,
    )
    prompt_blueprint = render_prompt(
        "parse_question",
        question=question,
        allowed_scope=allowed_scope or ["documents", "chunks", "graph", "cases"],
    )
    analysis_notes.append(f"解析提示词已加载，长度 {len(prompt_blueprint)} 字符。")

    return {
        "question_type": question_type,
        "entities": entities,
        "relation_type": relation_type,
        "constraints": constraints,
        "need_multihop": need_multihop,
        "retrieval_strategy_hint": retrieval_strategy,
        "analysis_notes": analysis_notes,
    }

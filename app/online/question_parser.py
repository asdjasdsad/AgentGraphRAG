from __future__ import annotations

import json
import re
from typing import Any

from app.core.llm import PromptPackage, complete_prompt, try_parse_json
from app.prompts import render_prompt


COMPONENT_HINTS = ("液压泵", "密封圈", "阀门", "轴承", "传感器", "作动筒", "管路", "滤芯", "接头", "泵体")
PHENOMENON_HINTS = ("泄漏", "渗漏", "异响", "裂纹", "过热", "失效", "松动", "卡滞", "磨损", "振动")
CAUSE_HINTS = ("老化", "磨损", "腐蚀", "装配不良", "污染", "疲劳", "间隙过大", "密封失效", "超温")
ACTION_HINTS = ("更换", "维修", "整改", "校准", "复测", "清洗", "润滑", "加固", "排故")
CAUSE_KEYWORDS = ("原因", "根因", "为什么", "诱因", "导致", "追溯")
ACTION_KEYWORDS = ("措施", "建议", "整改", "维修", "怎么处理", "如何处理", "修复")
CASE_KEYWORDS = ("案例", "历史", "类似", "同类", "先例", "复现")
VERIFY_KEYWORDS = ("是否", "有没有", "闭环", "验证", "确认", "核验")
MULTIHOP_KEYWORDS = ("根因链", "路径", "链路", "追溯", "多跳", "影响链")
CONSTRAINT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"Q\d{4}-\d{3,}", "issue_id"),
    (r"(?:最近三个月|近半年|近一年)", "time_window"),
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


def _infer_rule_result(question: str) -> dict[str, Any]:
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
    retrieval_strategy = "hybrid" if need_multihop or (entities and relation_type and has_case_intent) else "graph" if entities and relation_type else "vector"
    notes = [f"问题类型={question_type}", f"建议检索={retrieval_strategy}"]
    if entities:
        notes.append(f"识别实体：{', '.join(entities)}")
    if constraints:
        notes.append(f"约束：{'; '.join(constraints)}")
    return {
        "question_type": question_type,
        "entities": entities,
        "relation_type": relation_type,
        "constraints": constraints,
        "need_multihop": need_multihop,
        "retrieval_strategy_hint": retrieval_strategy,
        "analysis_notes": notes,
    }


def analyze_question(question: str, allowed_scope: list[str] | None = None) -> dict[str, Any]:
    rule_result = _infer_rule_result(question)
    prompt = render_prompt("parse_question", question=question, allowed_scope=allowed_scope or ["documents", "chunks", "graph", "cases"])
    llm_result = complete_prompt(role="reasoning", prompt=PromptPackage(system="你是问题解析代理，请输出 JSON。", user=prompt))
    parsed = try_parse_json(llm_result.content)
    if parsed:
        merged = dict(rule_result)
        for key in ("question_type", "entities", "relation_type", "constraints", "need_multihop", "retrieval_strategy_hint"):
            if key in parsed and parsed[key] not in (None, "", []):
                merged[key] = parsed[key]
        merged.setdefault("analysis_notes", [])
        merged["analysis_notes"] = list(rule_result.get("analysis_notes", [])) + [f"reasoning_model={llm_result.model}", f"reasoning_provider={llm_result.provider}"]
        return merged
    rule_result["analysis_notes"].append(f"reasoning_model={llm_result.model}")
    rule_result["analysis_notes"].append("LLM 未返回可解析 JSON，已退回规则解析")
    return rule_result

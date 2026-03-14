from __future__ import annotations

from app.domain.enums import RetrievalStrategy
from app.prompts import render_prompt


def route_retrieval(state: dict) -> dict:
    question = state.get("question", "")
    entities = state.get("entities", [])
    question_type = state.get("question_type", "knowledge_search")
    need_multihop = state.get("need_multihop", False)
    relation_type = state.get("relation_type") or ""
    prompt_blueprint = render_prompt(
        "route_retrieval",
        question=question,
        question_type=question_type,
        entities=entities,
        need_multihop=need_multihop,
        relation_type=relation_type or "(empty)",
    )

    if need_multihop:
        strategy = RetrievalStrategy.HYBRID
        reason = "问题包含根因追溯或多跳推理意图，先走 hybrid 同时补图关系和文本证据。"
    elif question_type in {"case_lookup", "verification_check"} and entities:
        strategy = RetrievalStrategy.HYBRID
        reason = "问题既要找历史案例/验证结论，又要回看原始文本细节，hybrid 更稳妥。"
    elif entities and relation_type:
        strategy = RetrievalStrategy.GRAPH
        reason = "实体和关系意图都比较明确，优先用 graph 追原因或措施链路。"
    else:
        strategy = RetrievalStrategy.VECTOR
        reason = "当前更像语义检索问题，先走 vector 找相关文本证据。"

    route_notes = [
        reason,
        f"实体数={len(entities)}，关系意图={relation_type or 'none'}，问题类型={question_type}。",
        f"路由提示词已加载，长度 {len(prompt_blueprint)} 字符。",
    ]
    return {"retrieval_strategy": strategy, "route_reason": reason, "route_notes": route_notes}

from __future__ import annotations

from app.domain.enums import RetrievalStrategy
from app.prompts import render_prompt


def route_retrieval(state: dict) -> dict:
    question = state.get("question", "")
    entities = state.get("entities", [])
    question_type = state.get("question_type", "knowledge_search")
    need_multihop = state.get("need_multihop", False)
    relation_type = state.get("relation_type") or ""
    render_prompt("route_retrieval", question=question, question_type=question_type, entities=entities, need_multihop=need_multihop, relation_type=relation_type or "(empty)")
    if need_multihop:
        strategy = RetrievalStrategy.HYBRID
        reason = "问题存在多跳追溯意图，优先走 hybrid 联合图谱、向量和案例记忆。"
    elif question_type in {"case_lookup", "verification_check"} and entities:
        strategy = RetrievalStrategy.HYBRID
        reason = "问题既需要看历史案例，也需要核对原始文本细节。"
    elif entities and relation_type:
        strategy = RetrievalStrategy.GRAPH
        reason = "实体和关系意图比较明确，优先走图检索。"
    else:
        strategy = RetrievalStrategy.VECTOR
        reason = "当前更像语义搜索问题，先从文本证据开始。"
    route_notes = [reason, f"entities={len(entities)}", f"relation_type={relation_type or 'none'}", f"question_type={question_type}"]
    return {"retrieval_strategy": strategy, "route_reason": reason, "route_notes": route_notes}

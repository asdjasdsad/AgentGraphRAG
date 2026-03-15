from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import RetrievalStrategy
from app.domain.schemas import QAState
from app.online.answer_generator import generate_final_answer
from app.online.query_builder import build_query_plan
from app.online.question_parser import analyze_question
from app.online.rerank import rerank_evidence
from app.online.retrieve_graph import retrieve_graph_evidence
from app.online.retrieve_hybrid import retrieve_hybrid_evidence
from app.online.retrieve_vector import retrieve_vector_evidence
from app.online.router import route_retrieval
from app.online.verifier import verify_evidence


@dataclass
class AgentExecution:
    role: str
    summary: str
    details: dict[str, Any]


class QueryRouterAgent:
    role = "query_router"

    def run(self, state: QAState) -> AgentExecution:
        parsed = analyze_question(state.question, state.allowed_scope)
        for key, value in parsed.items():
            if hasattr(state, key):
                setattr(state, key, value)
        routing = route_retrieval(state.model_dump())
        for key, value in routing.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return AgentExecution(
            role=self.role,
            summary=f"解析问题并确定检索策略为 {state.retrieval_strategy.value}",
            details={
                "question_type": state.question_type,
                "entities": state.entities,
                "relation_type": state.relation_type,
                "retrieval_strategy": state.retrieval_strategy.value,
                "analysis_notes": state.analysis_notes,
                "route_notes": state.route_notes,
            },
        )


class RetrievalAgent:
    role = "retrieval"

    def run(self, state: QAState) -> AgentExecution:
        state.query_plan = build_query_plan(state.model_dump())
        if state.retrieval_strategy == RetrievalStrategy.GRAPH:
            retrieved = retrieve_graph_evidence(state.model_dump())
        elif state.retrieval_strategy == RetrievalStrategy.HYBRID:
            retrieved = retrieve_hybrid_evidence(state.model_dump())
        else:
            retrieved = retrieve_vector_evidence(state.model_dump())
        for key, value in retrieved.items():
            if hasattr(state, key):
                setattr(state, key, value)
        ranked = rerank_evidence(state.model_dump())
        for key, value in ranked.items():
            if hasattr(state, key):
                setattr(state, key, value)
        state.retrieval_notes = [
            f"query_plan.strategy={state.query_plan.retrieval_strategy.value}",
            f"top_k={state.query_plan.top_k}",
            f"graph_hits={len(state.graph_hits)}",
            f"vector_hits={len(state.vector_hits)}",
        ]
        return AgentExecution(
            role=self.role,
            summary=f"完成 {state.retrieval_strategy.value} 检索并重排证据",
            details={
                "query_plan": state.query_plan.model_dump(mode="json"),
                "retrieval_notes": state.retrieval_notes,
                "top_evidence": [item.model_dump(mode="json") for item in state.reranked_evidence[:3]],
            },
        )


class GraphReasoningAgent:
    role = "graph_reasoning"

    def run(self, state: QAState) -> AgentExecution:
        if not state.reasoning_path and state.reranked_evidence:
            state.reasoning_path = [
                {
                    "step": index + 1,
                    "source": item.source,
                    "evidence_id": item.evidence_id,
                    "summary": item.content[:180],
                }
                for index, item in enumerate(state.reranked_evidence[:5])
            ]
        return AgentExecution(
            role=self.role,
            summary="将重排后的图谱与文本证据整理为可解释推理路径",
            details={"reasoning_path": state.reasoning_path[:5]},
        )


class VerificationAgent:
    role = "verification"

    def run(self, state: QAState) -> AgentExecution:
        verified = verify_evidence(state.model_dump())
        for key, value in verified.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return AgentExecution(
            role=self.role,
            summary=f"完成证据充分性校验，fallback_mode={state.fallback_mode}",
            details={
                "is_sufficient": state.is_sufficient,
                "conflict_detected": state.conflict_detected,
                "verification_notes": state.verification_notes,
            },
        )


class AnswerSynthesisAgent:
    role = "answer_synthesis"

    def run(self, state: QAState) -> AgentExecution:
        answer = generate_final_answer(state.model_dump())
        state.final_answer = answer["final_answer"]
        state.answer_payload = answer["answer_payload"]
        return AgentExecution(
            role=self.role,
            summary="生成最终答案和证据回显",
            details={
                "answer_model": state.answer_payload.get("answer_model"),
                "answer_provider": state.answer_payload.get("answer_provider"),
                "fallback": state.answer_payload.get("answer_fallback"),
            },
        )

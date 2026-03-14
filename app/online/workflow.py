from __future__ import annotations

from app.domain.enums import RetrievalStrategy
from app.domain.schemas import AskRequest, AskResponse, QAState
from app.online.answer_generator import generate_final_answer
from app.online.query_builder import build_query_plan
from app.online.question_parser import analyze_question
from app.online.rerank import rerank_evidence
from app.online.retrieve_graph import retrieve_graph_evidence
from app.online.retrieve_hybrid import retrieve_hybrid_evidence
from app.online.retrieve_vector import retrieve_vector_evidence
from app.online.router import route_retrieval
from app.online.verifier import verify_evidence
from app.risk.audit import write_audit_log
from app.risk.risk_classifier import classify_risk
from app.risk.risk_rules import allowed_scope_for_user


class GraphRAGWorkflow:
    def run(self, request: AskRequest) -> AskResponse:
        state = QAState(user_id=request.user_id, conversation_id=request.conversation_id, question=request.question)
        state.allowed_scope = allowed_scope_for_user(request.user_id)

        parsed = analyze_question(request.question, state.allowed_scope)
        for key, value in parsed.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.risk_level = classify_risk(state.question, state.entities)
        routing = route_retrieval(state.model_dump())
        for key, value in routing.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.retrieval_strategy = routing["retrieval_strategy"]
        state.query_plan = build_query_plan(state.model_dump())

        if state.retrieval_strategy == RetrievalStrategy.GRAPH:
            data = retrieve_graph_evidence(state.model_dump())
        elif state.retrieval_strategy == RetrievalStrategy.HYBRID:
            data = retrieve_hybrid_evidence(state.model_dump())
        else:
            data = retrieve_vector_evidence(state.model_dump())
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)

        ranked = rerank_evidence(state.model_dump())
        for key, value in ranked.items():
            if hasattr(state, key):
                setattr(state, key, value)

        verified = verify_evidence(state.model_dump())
        for key, value in verified.items():
            if hasattr(state, key):
                setattr(state, key, value)

        if not state.is_sufficient and state.retrieval_strategy == RetrievalStrategy.GRAPH:
            state.retrieval_strategy = RetrievalStrategy.VECTOR
            state.route_reason = "图谱证据不足，自动回退到 vector 检索补全文本证据。"
            state.query_plan = build_query_plan(state.model_dump())
            fallback_data = retrieve_vector_evidence(state.model_dump())
            for key, value in fallback_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            ranked = rerank_evidence(state.model_dump())
            for key, value in ranked.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            verified = verify_evidence(state.model_dump())
            for key, value in verified.items():
                if hasattr(state, key):
                    setattr(state, key, value)

        answer = generate_final_answer(state.model_dump())
        state.final_answer = answer["final_answer"]
        state.answer_payload = answer["answer_payload"]
        write_audit_log(state)
        return AskResponse(
            trace_id=state.trace_id,
            answer=state.final_answer,
            evidence=state.reranked_evidence[:5],
            reasoning_path=state.reasoning_path,
            retrieval_strategy=state.retrieval_strategy,
            risk_level=state.risk_level,
            fallback_mode=state.fallback_mode,
        )


workflow = GraphRAGWorkflow()

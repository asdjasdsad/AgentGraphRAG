from __future__ import annotations

from app.domain.enums import RetrievalStrategy
from app.domain.schemas import AskRequest, AskResponse, QAState
from app.online.agents import AnswerSynthesisAgent, GraphReasoningAgent, QueryRouterAgent, RetrievalAgent, VerificationAgent
from app.risk.audit import write_audit_log
from app.risk.risk_classifier import classify_risk
from app.risk.risk_rules import allowed_scope_for_user


class GraphRAGWorkflow:
    def __init__(self) -> None:
        self.query_router = QueryRouterAgent()
        self.retrieval_agent = RetrievalAgent()
        self.graph_reasoning_agent = GraphReasoningAgent()
        self.verification_agent = VerificationAgent()
        self.answer_agent = AnswerSynthesisAgent()

    def _record_trace(self, state: QAState, execution) -> None:
        state.agent_traces.append({"role": execution.role, "summary": execution.summary, "details": execution.details})

    def run(self, request: AskRequest) -> AskResponse:
        state = QAState(user_id=request.user_id, conversation_id=request.conversation_id, question=request.question)
        state.allowed_scope = allowed_scope_for_user(request.user_id)
        state.risk_level = classify_risk(state.question, state.entities)

        self._record_trace(state, self.query_router.run(state))
        self._record_trace(state, self.retrieval_agent.run(state))
        self._record_trace(state, self.graph_reasoning_agent.run(state))
        self._record_trace(state, self.verification_agent.run(state))

        if not state.is_sufficient and state.retrieval_strategy == RetrievalStrategy.GRAPH:
            state.retrieval_strategy = RetrievalStrategy.HYBRID
            state.route_reason = "图证据不足，自动回退到 hybrid 补充文本和案例证据。"
            self._record_trace(state, self.retrieval_agent.run(state))
            self._record_trace(state, self.graph_reasoning_agent.run(state))
            self._record_trace(state, self.verification_agent.run(state))

        self._record_trace(state, self.answer_agent.run(state))
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

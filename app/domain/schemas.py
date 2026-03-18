from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.enums import ChunkType, DocumentType, JobStatus, RetrievalStrategy, RiskLevel


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class DocumentUploadResponse(BaseModel):
    document_id: str
    file_name: str
    storage_path: str
    status: str


class DocumentMetadata(BaseModel):
    document_id: str = Field(default_factory=lambda: new_id("doc"))
    file_name: str
    file_type: str
    doc_type: DocumentType = DocumentType.UNKNOWN
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    source_type: str = "unstructured"
    source_system: str = "upload"
    parse_status: str = "pending"
    storage_path: str | None = None


class ParsedSection(BaseModel):
    section_path: str
    content: str
    page_no: int | None = None


class ParsedStep(BaseModel):
    step_no: int
    content: str


class ParsedDocument(BaseModel):
    document_id: str
    file_name: str
    doc_type: DocumentType
    pages: list[dict[str, Any]] = Field(default_factory=list)
    records: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[ParsedSection] = Field(default_factory=list)
    steps: list[ParsedStep] = Field(default_factory=list)
    validation: str | None = None
    headings: list[str] = Field(default_factory=list)
    table_headers: list[str] = Field(default_factory=list)
    raw_text: str = ""


class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: new_id("chunk"))
    document_id: str
    doc_type: DocumentType
    chunk_type: ChunkType
    section_path: str
    content: str
    page_no: int | None = None
    issue_id: str | None = None
    component: list[str] = Field(default_factory=list)
    source_type: str = "unstructured"
    load_batch_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    name: str
    type: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    source: str
    type: str
    target: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


class IngestionJob(BaseModel):
    job_id: str = Field(default_factory=lambda: new_id("job"))
    source_type: str
    batch_id: str = Field(default_factory=lambda: new_id("batch"))
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    error_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class StructuredRecord(BaseModel):
    issue_id: str
    phenomenon: str
    component: list[str] = Field(default_factory=list)
    cause: list[str] = Field(default_factory=list)
    action: list[str] = Field(default_factory=list)
    source_type: str = "structured"
    source_system: str = "api"
    load_batch_id: str | None = None


class AskRequest(BaseModel):
    question: str
    conversation_id: str
    user_id: str


class QueryPlan(BaseModel):
    retrieval_strategy: RetrievalStrategy
    query_text: str
    cypher_query: str | None = None
    cypher_params: dict[str, Any] = Field(default_factory=dict)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5
    max_hops: int = 2


class Evidence(BaseModel):
    evidence_id: str
    source: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class QAState(BaseModel):
    trace_id: str = Field(default_factory=lambda: new_id("trace"))
    user_id: str
    conversation_id: str
    question: str
    question_type: str | None = None
    entities: list[str] = Field(default_factory=list)
    relation_type: str | None = None
    constraints: list[str] = Field(default_factory=list)
    analysis_notes: list[str] = Field(default_factory=list)
    need_multihop: bool = False
    retrieval_strategy_hint: str | None = None
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.VECTOR
    route_reason: str = ""
    route_notes: list[str] = Field(default_factory=list)
    retrieval_notes: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    allowed_scope: list[str] = Field(default_factory=list)
    query_plan: QueryPlan | None = None
    vector_hits: list[Evidence] = Field(default_factory=list)
    graph_hits: list[Evidence] = Field(default_factory=list)
    case_hits: list[Evidence] = Field(default_factory=list)
    retrieved_evidence: list[Evidence] = Field(default_factory=list)
    reranked_evidence: list[Evidence] = Field(default_factory=list)
    agent_traces: list[dict[str, Any]] = Field(default_factory=list)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    is_sufficient: bool = False
    conflict_detected: bool = False
    verification_notes: list[str] = Field(default_factory=list)
    fallback_mode: str = "none"
    final_answer: str = ""
    answer_payload: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    trace_id: str
    answer: str
    evidence: list[Evidence]
    reasoning_path: list[dict[str, Any]]
    retrieval_strategy: RetrievalStrategy
    risk_level: RiskLevel
    fallback_mode: str


class CaseSummary(BaseModel):
    case_id: str = Field(default_factory=lambda: new_id("case"))
    issue_type: str
    summary: str
    root_cause_chain_json: list[str] = Field(default_factory=list)
    actions_json: list[str] = Field(default_factory=list)
    source_docs_json: list[str] = Field(default_factory=list)


class AuditLog(BaseModel):
    trace_id: str
    user_id: str
    question: str
    route: str
    risk_level: RiskLevel
    final_answer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    evidence_ids: list[str] = Field(default_factory=list)
    fallback_mode: str = "none"
    agent_traces: list[dict[str, Any]] = Field(default_factory=list)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    answer_payload: dict[str, Any] = Field(default_factory=dict)

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RelationType(BaseModel):
    pattern: str
    source: str
    type: str
    target: str
    properties: list[str] = Field(default_factory=list)


class GraphSchema(BaseModel):
    node_types: dict[str, list[str]]
    relation_types: list[RelationType]
    property_keys: dict[str, list[str]] = Field(default_factory=dict)


class TaskTemplate(BaseModel):
    task_type: str
    question_type: str
    relation_type: str
    need_multihop: bool
    required_relations: list[str]
    max_hops: int
    must_include_component: bool = False
    must_include_source: bool = False
    must_return: list[str] = Field(default_factory=list)
    nl_template: str


class ParsedQuestion(BaseModel):
    question_type: str
    entities: list[str]
    relation_type: str
    constraints: list[str] = Field(default_factory=list)
    need_multihop: bool = False


class SchemaContext(BaseModel):
    node_types: dict[str, list[str]]
    relation_types: list[str]


class QueryConstraints(BaseModel):
    max_hops: int = 2
    must_filter_component: bool = False
    must_return: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)


class PromptInput(BaseModel):
    user_query: str
    parsed_question: ParsedQuestion
    schema_context: SchemaContext
    constraints: QueryConstraints


class QueryPlan(BaseModel):
    target_nodes: list[str]
    required_relations: list[str]
    filters: list[str]
    max_hops: int


class ModelOutput(BaseModel):
    query_plan: QueryPlan
    cypher: str


class ValidationResult(BaseModel):
    passed: bool
    syntax_passed: bool = False
    schema_passed: bool = False
    business_passed: bool = False
    execution_passed: bool = False
    errors: list[str] = Field(default_factory=list)
    score: float = 0.0


class CandidateRecord(BaseModel):
    candidate_id: str
    prompt_id: str
    source: str
    input: PromptInput
    output: ModelOutput
    validation: ValidationResult


class SFTRecord(BaseModel):
    prompt_id: str
    instruction: str
    input: dict[str, Any]
    output: dict[str, Any]
    split: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DPORecord(BaseModel):
    prompt_id: str
    prompt: dict[str, Any]
    chosen: dict[str, Any]
    rejected: dict[str, Any]
    split: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingArtifact(BaseModel):
    stage: str
    backend: str
    base_model: str
    dataset_path: str
    output_dir: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    command: list[str] = Field(default_factory=list)

from enum import Enum


class DocumentType(str, Enum):
    ISSUE_RECORD = "issue_record"
    ANALYSIS_REPORT = "analysis_report"
    ACTION_REPORT = "action_report"
    UNKNOWN = "unknown"


class ChunkType(str, Enum):
    PHENOMENON = "phenomenon"
    COMPONENT = "component"
    CAUSE_ANALYSIS = "cause_analysis"
    ACTION = "action"
    VALIDATION = "validation"
    CASE_PROCESS = "case_process"
    GENERAL = "general"


class RetrievalStrategy(str, Enum):
    GRAPH = "graph"
    VECTOR = "vector"
    HYBRID = "hybrid"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

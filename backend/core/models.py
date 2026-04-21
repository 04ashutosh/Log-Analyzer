from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class LogLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARN = "WARN"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    UNKNOWN = "UNKNOWN"

class LogFormat(str, Enum):
    JSON = "json"
    JAVA = "java"
    PYTHON = "python"
    NODEJS = "nodejs"
    PLAINTEXT = "plaintext"
    UNKNOWN = "unknown"

class LogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw: str
    timestamp: Optional[datetime] = None
    level: LogLevel = LogLevel.UNKNOWN
    service: Optional[str] = None
    message: str = ""                    # ← was missing
    stack_trace: Optional[str] = None    # ← was missing
    format: LogFormat = LogFormat.UNKNOWN
    line_number: int = 0
    extra: Dict[str, Any] = Field(default_factory=dict)
    is_malformed: bool = False
    cluster_id: Optional[int] = None
    drain_template: Optional[str] = None
    outlier_score: float = 0.0


class ClusterSummary(BaseModel):
    cluster_id: int
    template: str
    frequency: int
    severity: str
    services: List[str] = Field(default_factory=list)
    is_root_cause: bool = False
    is_noise: bool = False
    representative_log: Optional[LogEntry] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    cascade_sources: List[int] = Field(default_factory=list)

class RecommendationResult(BaseModel):  # ← typo fixed (was RecommedationResult)
    cluster_id: int
    title: str
    probable_cause: str
    fix_steps: List[str]
    confidence: float
    source: str # "rule_engine" | "gemini" | "fallback"
    tags: List[str] = Field(default_factory=list)
    severity_assessment: str = ""
    rule_id: Optional[str] = None

class AnalysisResult(BaseModel):
    session_id: str
    status: str = "processing" #"processing" | "complete" | "error"
    total_logs: int = 0
    parsed_logs: int = 0  # ← typo fixed (was parsed_log)
    malformed_logs: int = 0
    unique_clusters: int = 0
    noise_logs: int = 0
    critical_count: int = 0
    error_count: int = 0
    warn_count: int = 0
    clusters: List[ClusterSummary] = Field(default_factory=list)
    recommendations: Dict[str, RecommendationResult] = Field(default_factory=dict)
    processing_time_ms: float = 0.0
    ai_available: bool = False
    error_message: Optional[str] = None

class IngestResponse(BaseModel):
    session_id: str
    status: str
    logs_received: int
    message: str

class RuleModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern: str # regex matched against log message + template
    title: str
    probable_cause: str
    fix_steps: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    severity_assessment: str = ""
    enabled: bool = True
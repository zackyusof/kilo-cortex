"""Data models for Kilo Cortex API interactions."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"
    emotional = "emotional"
    perceptual = "perceptual"


class MemoryCreate(BaseModel):
    content: str
    memory_type: MemoryType = MemoryType.episodic
    sector: Optional[str] = None
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    sector: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class MemoryResponse(BaseModel):
    id: int
    content: str
    memory_type: str
    sector: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int
    page: int
    page_size: int


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    sector: Optional[str] = None
    threshold: Optional[float] = None


class VectorSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    query: str
    total: int


class FulltextSearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 20
    sector: Optional[str] = None


class FulltextSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class HybridSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    vector_weight: float = 0.5
    text_weight: float = 0.5
    sector: Optional[str] = None


class HybridSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    query: str
    total: int


class SemanticSearchRequest(BaseModel):
    query: str
    cluster_size: int = 5
    top_k: int = 20


class SemanticSearchResponse(BaseModel):
    clusters: list[dict[str, Any]]
    total: int


class SessionCreate(BaseModel):
    name: Optional[str] = None
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    id: str
    name: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: str
    memory_count: int


class RulesRequest(BaseModel):
    limit: int = 50
    category: Optional[str] = None


class RuleResponse(BaseModel):
    id: int
    rule: str
    category: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str


class RuleCreate(BaseModel):
    rule: str
    category: Optional[str] = None
    confidence: Optional[float] = None


class PatternResponse(BaseModel):
    id: int
    trigger: str
    response_template: str
    enabled: bool
    created_at: str


class StatsResponse(BaseModel):
    total_memories: int
    memories_by_type: dict[str, int]
    total_sessions: int
    total_rules: int
    total_patterns: int
    vector_store_size: int
    last_ingested: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]


class IngestRequest(BaseModel):
    source: str
    data: list[dict[str, Any]]
    memory_type: Optional[MemoryType] = None


class ExportFormat(str, Enum):
    json = "json"
    csv = "csv"
    markdown = "markdown"


class ExportRequest(BaseModel):
    format: ExportFormat = ExportFormat.json
    filter_sector: Optional[str] = None
    limit: Optional[int] = None

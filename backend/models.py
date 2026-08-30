"""
Dependency Domino - Data Models
Pydantic models for all entities in the system
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class Language(str, Enum):
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSX = "jsx"
    TSX = "tsx"
    PYTHON = "python"
    CSS = "css"
    HTML = "html"
    JSON = "json"
    YAML = "yaml"
    OTHER = "other"


class NodeType(str, Enum):
    FILE = "file"
    FUNCTION = "function"
    TEST = "test"
    SERVICE = "service"
    API = "api"
    MODULE = "module"


class RelationshipType(str, Enum):
    IMPORT = "import"
    REQUIRE = "require"
    EXPORT = "export"
    CALLS = "calls"
    INHERITS = "inherits"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


# ─── Repository models ────────────────────────────────────────────────────────

class LanguageStat(BaseModel):
    language: str
    count: int
    percentage: float


class Repository(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    source: str  # "upload" | "demo" | "path"
    total_files: int = 0
    total_lines: int = 0
    languages: List[LanguageStat] = []
    directories: int = 0
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    analyzed_at: Optional[str] = None
    upload_path: Optional[str] = None
    is_demo: bool = False


class RepositoryResponse(BaseModel):
    repository: Repository
    message: str = "OK"


# ─── Component / Node models ──────────────────────────────────────────────────

class ComponentMetadata(BaseModel):
    lines: int = 0
    functions: List[str] = []
    imports: List[str] = []
    exports: List[str] = []
    is_test: bool = False
    is_entry_point: bool = False
    complexity: int = 0


class Component(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str
    name: str
    path: str
    type: NodeType = NodeType.FILE
    language: Language = Language.OTHER
    risk: RiskLevel = RiskLevel.UNKNOWN
    risk_score: float = 0.0
    metadata: ComponentMetadata = Field(default_factory=ComponentMetadata)
    direct_dependency_count: int = 0
    indirect_dependency_count: int = 0
    dependent_count: int = 0
    test_count: int = 0


# ─── Dependency / Edge models ─────────────────────────────────────────────────

class Dependency(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str  # component id
    target: str  # component id
    source_path: str = ""
    target_path: str = ""
    relationship: RelationshipType = RelationshipType.IMPORT
    dependency_type: DependencyType = DependencyType.DIRECT
    confidence: float = 1.0  # 0.0–1.0
    raw_import: str = ""  # the raw import string as parsed


# ─── Graph models ─────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    name: str
    path: str
    type: NodeType
    language: Language
    risk: RiskLevel
    risk_score: float
    metadata: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: RelationshipType
    dependency_type: DependencyType
    confidence: float


class DependencyGraph(BaseModel):
    repository_id: str
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    node_count: int = 0
    edge_count: int = 0


# ─── Impact analysis models ───────────────────────────────────────────────────

class RiskFactor(BaseModel):
    factor: str
    weight: float
    description: str


class ImpactAnalysis(BaseModel):
    component_id: str
    component_path: str
    impact_score: float  # 0–100
    risk_level: RiskLevel
    direct_dependencies: List[str] = []
    indirect_dependencies: List[str] = []
    dependents: List[str] = []
    affected_components: List[str] = []
    related_tests: List[str] = []
    risk_factors: List[RiskFactor] = []
    score_explanation: str = ""
    insufficient_data: bool = False
    computed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Test recommendation models ───────────────────────────────────────────────

class TestRecommendation(BaseModel):
    component_id: str
    existing_tests: List[str] = []
    recommended_tests: List[str] = []
    coverage_gaps: List[str] = []
    ai_generated: bool = False
    ai_available: bool = False
    ai_source: str = ""          # "watsonx" | "rule-based"
    fallback_reason: str = ""
    label: str = "AI-generated test recommendation"
    disclaimer: str = (
        "This test plan is AI-generated and not guaranteed to be complete. "
        "Review and supplement with domain knowledge."
    )
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── AI Explanation models ────────────────────────────────────────────────────

class AIExplanation(BaseModel):
    model_config = {"protected_namespaces": ()}

    component_id: str
    summary: str = ""
    why_it_matters: str = ""
    potential_impact: str = ""
    risk_factors: List[str] = []
    recommended_actions: List[str] = []
    test_recommendations: List[str] = []
    uncertainties: List[str] = []
    # Provenance – what was detected vs. inferred vs. unknown
    detected_dependencies: List[str] = []
    inferred_relationships: List[str] = []
    possible_impacts: List[str] = []
    ai_available: bool = False
    ai_source: str = ""   # "watsonx" | "rule-based" | "unavailable"
    model_used: str = ""
    fallback_reason: str = ""   # non-empty when AI was attempted but failed
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Risk assessment models ───────────────────────────────────────────────────

class RiskAssessment(BaseModel):
    repository_id: str
    total_components: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    unknown_count: int = 0
    weak_test_coverage_count: int = 0
    top_risk_components: List[Component] = []
    computed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Report models ────────────────────────────────────────────────────────────

class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str
    repository_name: str
    component_id: str
    component_path: str
    impact_score: float
    risk_level: RiskLevel
    direct_dependencies: List[str] = []
    indirect_dependencies: List[str] = []
    affected_components: List[str] = []
    related_tests: List[str] = []
    risk_factors: List[str] = []
    ai_explanation: Optional[AIExplanation] = None
    recommended_actions: List[str] = []
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Request / Response schemas ───────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    repository_id: str


class ImpactRequest(BaseModel):
    component_id: str


class ExplainRequest(BaseModel):
    component_id: str
    change_description: Optional[str] = None


class TestPlanRequest(BaseModel):
    component_id: str
    change_description: Optional[str] = None


class ReportRequest(BaseModel):
    repository_id: str
    component_id: str
    include_ai: bool = True


class SimulateRequest(BaseModel):
    component_id: str
    change_description: str


class SimulationResult(BaseModel):
    component_id: str
    change_description: str
    affected_components: List[str] = []
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_factors: List[str] = []
    recommended_tests: List[str] = []
    ai_consequence_summary: str = ""
    ai_available: bool = False


class SearchRequest(BaseModel):
    query: str
    repository_id: Optional[str] = None


class SearchResult(BaseModel):
    id: str
    name: str
    path: str
    type: NodeType
    language: Language
    risk_score: float
    snippet: str = ""

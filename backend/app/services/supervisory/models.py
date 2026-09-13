"""
ULPF Phase 7 Supervisory Intelligence Pydantic Data Models.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CapabilityScoreDetail(BaseModel):
    capability_name: str  # One of 8 dimensions
    score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    indicators: List[str] = Field(default_factory=list)
    positive_signals: List[str] = Field(default_factory=list)
    negative_signals: List[str] = Field(default_factory=list)
    supporting_evidence: Dict[str, Any] = Field(default_factory=dict)
    explanation: str


class SupervisoryRiskIndicatorDTO(BaseModel):
    entity_id: str
    entity_name: str
    score: float = Field(..., ge=0.0, le=100.0)
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    confidence: float = Field(..., ge=0.0, le=1.0)
    contributing_indicators: List[str] = Field(default_factory=list)
    evidence_count: int
    affected_capabilities: List[str] = Field(default_factory=list)
    trend: str  # IMPROVING, STABLE, DETERIORATING, INSUFFICIENT_EVIDENCE
    explanation: str
    generated_at: datetime


class ExecutionGapFinding(BaseModel):
    id: str
    entity_id: str
    indicator: str
    severity: str
    evidence: Dict[str, Any]
    time_period: str
    confidence: float
    explanation: str
    recommended_manual_review: str
    status: str = "OPEN"


class NegativeSpaceIndicator(BaseModel):
    id: str
    entity_id: str
    indicator_type: str
    title: str
    severity: str
    confidence: float
    evidence: Dict[str, Any]
    explanation: str
    recommended_manual_review: str


class ReviewSampleDTO(BaseModel):
    id: str
    entity_id: str
    event_id: str
    raw_event_id: str
    priority_label: str  # PRIORITY 1, PRIORITY 2, PRIORITY 3, ROUTINE
    priority_score: float
    reasons: List[str]
    capability_tags: List[str]
    severity: str
    anomaly_score: float
    closure_time_seconds: Optional[float] = None
    timestamp: datetime


class PeerMetricComparison(BaseModel):
    metric_name: str
    entity_value: float
    peer_median: float
    peer_p25: float
    peer_p75: float
    deviation_percent: float
    assessment_phrase: str  # Neutral supervisory phrasing


class PeerBenchmarkingDTO(BaseModel):
    entity_id: str
    peer_group: str
    peer_count: int
    metrics: List[PeerMetricComparison]
    summary_explanation: str


class TrendAnalysisDTO(BaseModel):
    entity_id: str
    current_period: str
    previous_period: str
    trend_status: str  # IMPROVING, STABLE, DETERIORATING, INSUFFICIENT_EVIDENCE
    overall_score_change: float
    capability_changes: Dict[str, float]
    explanation: str


class EvidenceChainDTO(BaseModel):
    finding_id: str
    finding_title: str
    finding_type: str
    severity: str
    confidence: float
    indicator_summary: Dict[str, Any]
    supporting_metrics: Dict[str, Any]
    underlying_event_ids: List[str]
    raw_event_samples: List[Dict[str, Any]]  # Includes sha256_hash, payload_excerpt, raw_event_id
    sha256_verification_passed: bool


class EntityAssessmentResponse(BaseModel):
    id: str
    entity_id: str
    entity_name: str
    assessment_period: str
    overall_score: float
    detection_score: float
    investigation_score: float
    escalation_score: float
    operational_discipline_score: float
    monitoring_coverage_score: float
    data_quality_score: float
    cyber_resilience_indicator: float
    confidence: float
    risk_category: str
    trend: str
    generated_at: datetime
    capabilities: List[CapabilityScoreDetail]
    supervisory_risk_indicator: SupervisoryRiskIndicatorDTO
    top_execution_gaps: List[ExecutionGapFinding]
    negative_space_indicators: List[NegativeSpaceIndicator]
    priority_samples: List[ReviewSampleDTO]
    peer_benchmarking: PeerBenchmarkingDTO
    trend_analysis: TrendAnalysisDTO


class ReviewSubmissionRequest(BaseModel):
    reviewer: str = Field(..., min_length=1)
    decision: str  # OPEN, UNDER_REVIEW, CONFIRMED, DISMISSED, INSUFFICIENT_EVIDENCE
    notes: str = Field(..., min_length=1)


class ReviewAuditDTO(BaseModel):
    id: str
    indicator_id: str
    reviewer: str
    previous_status: str
    decision: str
    notes: str
    timestamp: datetime

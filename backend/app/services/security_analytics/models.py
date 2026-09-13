from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    SUSPICIOUS = "SUSPICIOUS"
    INACTIVE = "INACTIVE"


class PriorityCategory(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingType(str, Enum):
    ANOMALY = "ANOMALY"
    SOURCE_GAP = "SOURCE_GAP"
    VOLUME_SPIKE = "VOLUME_SPIKE"
    VOLUME_DROP = "VOLUME_DROP"
    COVERAGE_GAP = "COVERAGE_GAP"
    CORRELATION = "CORRELATION"
    DATA_QUALITY = "DATA_QUALITY"
    UNKNOWN_FORMAT = "UNKNOWN_FORMAT"
    PARSER_FAILURE = "PARSER_FAILURE"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"


class AnalyticsFilter(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    vendor: Optional[str] = None
    severity: Optional[str] = None
    source_id: Optional[str] = None
    device_type: Optional[str] = None


class SecurityOverview(BaseModel):
    total_events: int = 0
    total_sources: int = 0
    healthy_sources_count: int = 0
    degraded_sources_count: int = 0
    suspicious_sources_count: int = 0
    inactive_sources_count: int = 0
    open_findings_count: int = 0
    critical_findings_count: int = 0
    high_findings_count: int = 0
    coverage_gaps_count: int = 0
    correlation_candidates_count: int = 0
    anomaly_count: int = 0
    unknown_format_count: int = 0
    parser_failure_count: int = 0
    validation_failure_count: int = 0
    data_quality_index: float = 100.0  # 0 to 100 score


class SourceHealthMetrics(BaseModel):
    source_id: str
    name: str
    vendor: str
    device_type: str
    status: HealthStatus
    total_events: int
    events_per_hour: float
    avg_hourly_volume: float
    last_event_timestamp: Optional[datetime]
    parsing_success_rate: float
    validation_failure_rate: float
    anomaly_rate: float
    unknown_format_rate: float
    ingestion_gap_duration_minutes: float
    status_reason: str


class CoverageFindingItem(BaseModel):
    finding_type: str  # Potential monitoring gap, Potential telemetry reduction, etc.
    entity: str
    time_window: str
    confidence: float
    reason: str
    evidence: Dict[str, Any]


class BaselineMetrics(BaseModel):
    source_id: str
    avg_hourly_volume: float
    median_hourly_volume: float
    stddev_hourly_volume: float
    severity_distribution: Dict[str, float]
    protocol_distribution: Dict[str, float]
    action_distribution: Dict[str, float]
    sample_hours_count: int
    calculated_at: datetime


class BaselineDeviationItem(BaseModel):
    source_id: str
    deviation_type: str  # VOLUME_SPIKE, VOLUME_DROP, UNUSUAL_SEVERITY, etc.
    baseline_value: float
    current_value: float
    deviation_percentage: float
    z_score: float
    explanation: str


class CorrelationGroup(BaseModel):
    correlation_id: str
    matching_key: str  # e.g., source_ip=10.0.0.1
    shared_entity_type: str  # source_ip, destination_ip, asset, user, destination_port
    shared_entity_value: str
    event_count: int
    distinct_sources_count: int
    distinct_vendors: List[str]
    time_window_seconds: int
    first_seen: datetime
    last_seen: datetime
    events_preview: List[Dict[str, Any]]
    explanation: str


class FindingResponse(BaseModel):
    id: str
    finding_type: str
    severity: str
    confidence: float
    priority_score: float
    priority_category: str
    source_id: Optional[str]
    event_count: int
    first_seen: datetime
    last_seen: datetime
    title: str
    explanation: str
    evidence: Dict[str, Any]
    recommended_action: Optional[str]
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AnalyzeRunResponse(BaseModel):
    scan_id: str
    scan_timestamp: datetime
    sources_scanned: int
    findings_generated: int
    new_findings_count: int
    health_summary: Dict[str, int]

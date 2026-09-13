from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrainingResult(BaseModel):
    """Telemetry report after fitting the offline anomaly baseline."""
    model_name: str
    model_version: str
    records_trained: int
    duration_seconds: float
    status: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ScanResult(BaseModel):
    """Telemetry report after scanning normalized events for anomalies."""
    records_scanned: int
    anomalies_detected: int
    normal_detected: int
    duration_seconds: float
    status: str


class AnomalyScoreItem(BaseModel):
    """Detailed anomaly scoring record for a specific event."""
    id: str
    event_id: str
    model_name: str
    model_version: str
    anomaly_score: float
    is_anomaly: bool
    detected_at: datetime
    feature_summary: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None


class AnomalyStatistics(BaseModel):
    """Aggregated anomaly metrics and current detector status."""
    total_scanned: int
    total_anomalies: int
    anomaly_rate: float
    model_name: str
    model_version: str
    is_model_trained: bool

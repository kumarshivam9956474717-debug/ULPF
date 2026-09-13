from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OverviewMetrics(BaseModel):
    """High-level system telemetry and event rate metrics."""
    total_events: int = 0
    total_raw_events: int = 0
    events_per_minute: float = 0.0
    events_per_hour: float = 0.0
    validation_failures: int = 0
    parser_failures: int = 0
    anomaly_count: int = 0


class TimelinePoint(BaseModel):
    """Time-bucketed aggregation for event frequency trends."""
    timestamp: str
    count: int
    errors: int = 0


class DistributionItem(BaseModel):
    """Categorical distribution representation."""
    key: str
    count: int
    percentage: float = 0.0


class TopItem(BaseModel):
    """Ranking of top network entities (IPs, ports, users)."""
    item: str
    count: int
    percentage: float = 0.0


class AnalyticsFilter(BaseModel):
    """Query filters for analytics endpoints."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    vendor: Optional[str] = None
    severity: Optional[str] = None
    device_type: Optional[str] = None

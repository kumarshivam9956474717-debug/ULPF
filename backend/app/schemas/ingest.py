from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FormatDetectionRequest(BaseModel):
    raw_payload: str = Field(..., description="Raw log string to analyze for format detection")


class FormatDetectionResponse(BaseModel):
    detected_format: str = Field(..., description="Identified format (cef, leef, json, syslog, csv, xml, unknown)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    reason: str = Field(..., description="Deterministic heuristic explanation")


class SingleIngestRequest(BaseModel):
    raw_payload: str = Field(..., description="Raw perimeter log event string")
    source_id: Optional[str] = Field(None, description="Optional registered log source ID")
    format_hint: Optional[str] = Field(None, description="Optional caller-specified format hint")


class SingleIngestResponse(BaseModel):
    success: bool
    raw_event_id: str
    normalized_event_id: Optional[str] = None
    detected_format: str
    parser_id: Optional[str] = None
    parser_version: Optional[str] = None
    validation_status: str
    onboarding_available: bool = False
    errors: List[str] = []
    warnings: List[str] = []
    normalized_event: Optional[Dict[str, Any]] = None


class BatchIngestRequest(BaseModel):
    events: List[str] = Field(..., max_length=5000, description="Bounded batch of raw log strings")
    source_id: Optional[str] = Field(None, description="Optional registered log source ID")


class BatchIngestResponse(BaseModel):
    processing_run_id: str
    total_received: int
    total_parsed: int
    total_normalized: int
    total_failed: int
    processing_time_ms: int
    format_statistics: Dict[str, int] = {}
    parser_statistics: Dict[str, int] = {}

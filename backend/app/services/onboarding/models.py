from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FieldCandidate(BaseModel):
    source_field: str
    sample_value: Optional[str] = None
    inferred_type: str = "string"  # ip, port, timestamp, protocol, action, severity, username, integer, string
    occurrence_rate: float = 1.0


class SuggestedMapping(BaseModel):
    source_field: str
    target_field: str
    confidence: float
    confidence_level: ConfidenceLevel
    method: str  # exact_alias, normalized_alias, datatype_inference, semantic_similarity, combined
    is_custom: bool = False
    transform: Optional[str] = "none"


class LogAnalysisRequest(BaseModel):
    sample_logs: List[str] = Field(..., min_length=1, description="One or more sample log records from unknown vendor")


class LogAnalysisResult(BaseModel):
    detected_format: str  # key_value, delimited, json, syslog_kv, unknown
    format_confidence: float
    delimiter: Optional[str] = " "
    kv_delimiter: Optional[str] = "="
    has_syslog_header: bool = False
    sample_count: int
    fields: List[FieldCandidate] = Field(default_factory=list)
    suggested_mappings: List[SuggestedMapping] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MappingRule(BaseModel):
    source_field: str
    target_field: str
    transform: Optional[str] = "none"
    is_custom: bool = False
    confidence: Optional[float] = 1.0


class MappingValidationRequest(BaseModel):
    sample_logs: List[str] = Field(..., min_length=1)
    source_format: str = "key_value"
    delimiter: Optional[str] = " "
    kv_delimiter: Optional[str] = "="
    mappings: List[MappingRule] = Field(default_factory=list)


class MappingValidationResult(BaseModel):
    is_valid: bool
    records_tested: int
    records_passed: int
    records_failed: int
    mapped_fields: List[str] = Field(default_factory=list)
    unmapped_fields: List[str] = Field(default_factory=list)
    custom_fields: List[str] = Field(default_factory=list)
    sample_normalized_preview: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    vendor: str = Field(..., min_length=2, max_length=64)
    product: str = Field(..., min_length=2, max_length=64)
    device_type: str = Field("security_device", max_length=32)
    source_format: str = Field("key_value", max_length=32)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    field_mappings: List[MappingRule] = Field(..., min_length=1)
    confidence: Optional[float] = 0.0
    created_by: Optional[str] = "user"


class ProfileUpdateRequest(BaseModel):
    vendor: Optional[str] = None
    product: Optional[str] = None
    device_type: Optional[str] = None
    source_format: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    field_mappings: Optional[List[MappingRule]] = None
    confidence: Optional[float] = None
    increment_version: bool = True
    actor: Optional[str] = "user"


class TestProfileRequest(BaseModel):
    __test__ = False
    profile_id: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    field_mappings: Optional[List[MappingRule]] = None
    sample_logs: List[str] = Field(..., min_length=1)


class AuditLogItem(BaseModel):
    id: str
    action: str
    version: str
    actor: Optional[str] = None
    summary: str
    timestamp: datetime


class ProfileResponse(BaseModel):
    id: str
    name: str
    vendor: str
    product: str
    device_type: str
    source_format: str
    parser_type: str
    configuration: Dict[str, Any]
    field_mappings: List[Dict[str, Any]]
    version: str
    status: str
    confidence: float
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    audit_logs: Optional[List[AuditLogItem]] = None

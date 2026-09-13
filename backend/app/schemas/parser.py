from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ParserVersionBase(BaseModel):
    version: str = Field(..., description="Semantic version string (e.g. 1.0.0)")
    checksum: str = Field(..., description="SHA-256 checksum of parser configuration/rules")
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Extraction configuration or regex rules")
    active: bool = Field(True, description="Whether this version is active for parsing")


class ParserVersionCreate(ParserVersionBase):
    pass


class ParserVersionResponse(ParserVersionBase):
    id: str
    parser_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParserBase(BaseModel):
    parser_id: str = Field(..., description="Unique slug for parser (e.g., cisco_asa_syslog)")
    name: str = Field(..., description="Display name of parser")
    vendor: str = Field(..., description="Target vendor")
    product: Optional[str] = Field(None, description="Target product family")
    device_type: Optional[str] = Field(None, description="Device role")
    supported_formats: List[str] = Field(default_factory=list, description="Formats handled (syslog, cef, json)")
    description: Optional[str] = Field(None, description="Parser description")
    enabled: bool = Field(True, description="Whether parser is enabled")


class ParserCreate(ParserBase):
    initial_version: Optional[ParserVersionBase] = None


class ParserResponse(ParserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    versions: List[ParserVersionResponse] = []

    model_config = ConfigDict(from_attributes=True)

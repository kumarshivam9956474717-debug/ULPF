from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LogSourceBase(BaseModel):
    source_id: str = Field(..., description="Unique logical identifier for the log source (e.g., FW-HQ-01)")
    vendor: Optional[str] = Field(None, description="Device vendor (e.g., Cisco, Palo Alto, Fortinet)")
    product: Optional[str] = Field(None, description="Product model or family (e.g., ASA 5585-X)")
    device_type: str = Field("firewall", description="Classification: firewall, ids, proxy, vpn, router")
    hostname: Optional[str] = Field(None, description="Hostname or reporting IP/FQDN")
    source_format: Optional[str] = Field(None, description="Expected log format: syslog, cef, leef, json")
    description: Optional[str] = Field(None, description="Operational notes or boundary context")
    enabled: bool = Field(True, description="Whether log collection from this source is active")


class LogSourceCreate(LogSourceBase):
    pass


class LogSourceResponse(LogSourceBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

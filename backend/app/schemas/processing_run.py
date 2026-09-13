from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProcessingRunResponse(BaseModel):
    id: str
    run_id: str = Field(..., description="Unique run identifier")
    source_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_received: int
    records_parsed: int
    records_normalized: int
    records_failed: int
    processing_time_ms: int
    error_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

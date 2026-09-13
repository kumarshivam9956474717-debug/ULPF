from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Parameters for exporting normalized events to Apache Parquet."""
    start_time: Optional[datetime] = Field(None, description="Optional start timestamp filter")
    end_time: Optional[datetime] = Field(None, description="Optional end timestamp filter")
    source_id: Optional[str] = Field(None, description="Optional log source ID filter")
    batch_size: Optional[int] = Field(10000, ge=100, le=50000, description="Chunked database extraction batch size")


class ExportMetrics(BaseModel):
    """Detailed operational metrics from a Parquet export run."""
    records_selected: int
    records_exported: int
    files_created: int
    bytes_written: int
    duration_seconds: float
    failed_records: int = 0
    partition_count: int
    file_paths: List[str] = Field(default_factory=list)


class ExportStatus(BaseModel):
    """Status of the export service and latest export run telemetry."""
    status: str
    export_directory: str
    last_export: Optional[ExportMetrics] = None

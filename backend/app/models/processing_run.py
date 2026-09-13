import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProcessingRun(Base):
    """
    Execution run and batch metrics tracking for log ingestion, parsing,
    and normalization cycles.
    """
    __tablename__ = "processing_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("log_sources.source_id", ondelete="SET NULL"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="started", nullable=False)  # started, completed, failed

    records_received = Column(Integer, default=0, nullable=False)
    records_parsed = Column(Integer, default=0, nullable=False)
    records_normalized = Column(Integer, default=0, nullable=False)
    records_failed = Column(Integer, default=0, nullable=False)
    processing_time_ms = Column(Integer, default=0, nullable=False)

    error_summary = Column(Text, nullable=True)

    # Relationships
    source = relationship("LogSource", back_populates="processing_runs")
    raw_events = relationship("RawEvent", back_populates="processing_run")
    validation_results = relationship("ValidationResult", back_populates="processing_run")

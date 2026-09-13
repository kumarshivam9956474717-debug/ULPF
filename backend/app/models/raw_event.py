import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, event, inspect
from sqlalchemy.orm import relationship
from app.core.database import Base


class RawEvent(Base):
    """
    Lossless, immutable raw event storage table.
    Guarantees raw data is never mutated or discarded.
    """
    __tablename__ = "raw_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_event_id = Column(String(64), unique=True, nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("log_sources.source_id", ondelete="SET NULL"), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    raw_payload = Column(Text, nullable=False)
    payload_encoding = Column(String(16), default="utf-8", nullable=False)
    payload_hash_sha256 = Column(String(64), nullable=False, index=True)
    source_format = Column(String(32), nullable=True)
    ingestion_batch_id = Column(String(64), ForeignKey("processing_runs.run_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    source = relationship("LogSource", back_populates="raw_events")
    normalized_events = relationship(
        "NormalizedEvent",
        back_populates="raw_event",
        cascade="all, delete-orphan",
        foreign_keys="NormalizedEvent.raw_event_id"
    )
    processing_run = relationship("ProcessingRun", back_populates="raw_events")


@event.listens_for(RawEvent, "before_update")
def enforce_raw_payload_immutability(mapper, connection, target):
    """
    Architecture Principle 1: Raw events must NEVER be modified or discarded.
    Enforces payload immutability at the ORM layer.
    """
    state = inspect(target)
    history = state.get_history("raw_payload", True)
    if history.has_changes():
        raise ValueError("Forensic violation: raw_payload is strictly immutable and cannot be modified after insertion.")

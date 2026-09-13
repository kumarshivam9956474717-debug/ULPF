import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class LogSource(Base):
    """
    Perimeter log emitter registry.
    Manages metadata for devices generating security events.
    """
    __tablename__ = "log_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(64), unique=True, nullable=False, index=True)
    vendor = Column(String(64), nullable=True, index=True)
    product = Column(String(64), nullable=True)
    device_type = Column(String(32), nullable=False, default="firewall", index=True)
    hostname = Column(String(255), nullable=True, index=True)
    source_format = Column(String(32), nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    raw_events = relationship("RawEvent", back_populates="source")
    processing_runs = relationship("ProcessingRun", back_populates="source")

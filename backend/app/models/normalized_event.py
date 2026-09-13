import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class NormalizedEvent(Base):
    """
    Standardized, analytics-ready event representation adhering to the
    Universal Event Schema (UES). Retains direct foreign key linkage to raw_events.
    """
    __tablename__ = "normalized_events"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identity & Traceability
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    source_event_id = Column(String(128), nullable=True)
    raw_event_id = Column(
        String(64),
        ForeignKey("raw_events.raw_event_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    schema_version = Column(String(16), default="1.0.0", nullable=False)

    # Time
    timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    ingestion_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    timezone = Column(String(32), default="UTC", nullable=True)

    # Source Device
    vendor = Column(String(64), nullable=True, index=True)
    product = Column(String(64), nullable=True)
    device_type = Column(String(32), nullable=True, index=True)
    device_id = Column(String(128), nullable=True)
    hostname = Column(String(255), nullable=True)
    source_format = Column(String(32), nullable=True)

    # Network
    source_ip = Column(String(45), nullable=True, index=True)
    source_port = Column(Integer, nullable=True)
    destination_ip = Column(String(45), nullable=True, index=True)
    destination_port = Column(Integer, nullable=True)
    protocol = Column(String(32), nullable=True)

    # User Identity
    username = Column(String(128), nullable=True)
    user_id = Column(String(128), nullable=True)
    authentication_method = Column(String(64), nullable=True)

    # Event Taxonomy
    event_type = Column(String(64), nullable=True, index=True)
    action = Column(String(32), nullable=True)
    outcome = Column(String(32), nullable=True)
    severity = Column(String(32), default="unknown", nullable=True, index=True)
    category = Column(String(64), nullable=True)
    subcategory = Column(String(64), nullable=True)

    # Network Context
    interface = Column(String(64), nullable=True)
    direction = Column(String(32), nullable=True)
    zone = Column(String(64), nullable=True)

    # Threat / Security
    threat_name = Column(String(255), nullable=True)
    threat_id = Column(String(128), nullable=True)
    signature_id = Column(String(128), nullable=True)
    rule_id = Column(String(128), nullable=True)

    # Additional
    message = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=True)
    custom_fields = Column(JSON, default=dict, nullable=True)

    # Traceability Metadata
    parser_id = Column(String(64), nullable=True)
    parser_version = Column(String(32), default="1.0.0", nullable=True)
    normalization_version = Column(String(32), default="1.0.0", nullable=False)

    # Relationships
    raw_event = relationship(
        "RawEvent",
        back_populates="normalized_events",
        foreign_keys=[raw_event_id]
    )
    validation_results = relationship(
        "ValidationResult",
        back_populates="normalized_event",
        cascade="all, delete-orphan",
        foreign_keys="ValidationResult.normalized_event_id"
    )

    __table_args__ = (
        Index("ix_normalized_events_src_dst_ip", "source_ip", "destination_ip"),
        Index("ix_normalized_events_ts_vendor", "timestamp", "vendor"),
    )

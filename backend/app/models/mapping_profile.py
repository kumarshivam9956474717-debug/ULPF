import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class LogMappingProfile(Base):
    """
    Persistent configuration profile for a no-code, human-in-the-loop
    onboarded log format. Used by ConfigurableParser to process future logs
    without modifying Python source code.
    """
    __tablename__ = "log_mapping_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False, index=True)
    vendor = Column(String(64), nullable=False, index=True)
    product = Column(String(64), nullable=False)
    device_type = Column(String(32), default="security_device", nullable=False)
    source_format = Column(String(32), default="key_value", nullable=False)  # key_value, delimited, json, syslog_kv
    parser_type = Column(String(64), default="configurable", nullable=False)

    # Parser extraction & structural settings (e.g., delimiter, kv_delimiter, headers)
    configuration = Column(JSON, default=dict, nullable=False)

    # Field mapping rules list: [{source_field, target_field, transform, is_custom, confidence}]
    field_mappings = Column(JSON, default=list, nullable=False)

    # Versioning and activation lifecycle
    version = Column(String(32), default="1.0.0", nullable=False)
    status = Column(String(32), default="DRAFT", nullable=False, index=True)  # DRAFT, ACTIVE, DISABLED
    confidence = Column(Float, default=0.0, nullable=False)

    created_by = Column(String(128), default="system", nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    audit_logs = relationship(
        "MappingAuditLog",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(MappingAuditLog.timestamp)"
    )

    __table_args__ = (
        Index("ix_mapping_profile_vendor_status", "vendor", "status"),
    )


class MappingAuditLog(Base):
    """
    Immutable audit trail for all mapping profile lifecycle events:
    creation, mapping modifications, validation testing, activation, and disabling.
    """
    __tablename__ = "mapping_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(
        String(36),
        ForeignKey("log_mapping_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    action = Column(String(64), nullable=False)  # CREATED, UPDATED, TESTED, ACTIVATED, DISABLED
    version = Column(String(32), nullable=False)
    actor = Column(String(128), default="system", nullable=True)
    summary = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    profile = relationship("LogMappingProfile", back_populates="audit_logs")

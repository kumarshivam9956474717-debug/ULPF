import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Parser(Base):
    """
    Parser registry model.
    Decouples vendor-specific parsing logic from normalization.
    """
    __tablename__ = "parsers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parser_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    vendor = Column(String(64), nullable=False, index=True)
    product = Column(String(64), nullable=True)
    device_type = Column(String(32), nullable=True)
    supported_formats = Column(JSON, default=list, nullable=False)  # e.g., ["syslog", "cef"]
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    versions = relationship("ParserVersion", back_populates="parser", cascade="all, delete-orphan")


class ParserVersion(Base):
    """
    Parser version registry for versioning parsing logic and regex configurations.
    """
    __tablename__ = "parser_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parser_id = Column(String(64), ForeignKey("parsers.parser_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA-256 hash of configuration
    configuration = Column(JSON, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    parser = relationship("Parser", back_populates="versions")

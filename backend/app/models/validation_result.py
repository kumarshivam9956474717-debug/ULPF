import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ValidationResult(Base):
    """
    Validation audit record for normalized events checking schema conformance,
    range restrictions, and data hygiene.
    """
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    normalized_event_id = Column(
        String(64),
        ForeignKey("normalized_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    run_id = Column(
        String(64),
        ForeignKey("processing_runs.run_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    validation_status = Column(String(32), default="valid", nullable=False)  # valid, invalid, warning
    validation_errors = Column(JSON, default=list, nullable=False)
    validation_warnings = Column(JSON, default=list, nullable=False)
    validation_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    normalized_event = relationship(
        "NormalizedEvent",
        back_populates="validation_results",
        foreign_keys=[normalized_event_id]
    )
    processing_run = relationship("ProcessingRun", back_populates="validation_results")

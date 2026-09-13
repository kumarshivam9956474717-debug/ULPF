import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class AnomalyResult(Base):
    """
    Persistence layer for offline anomaly detection results.
    Links directly to normalized events for auditability and full traceability.
    """
    __tablename__ = "anomaly_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(
        String(64),
        ForeignKey("normalized_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    model_name = Column(String(64), nullable=False, default="isolation_forest_baseline")
    model_version = Column(String(32), nullable=False, default="1.0.0")
    anomaly_score = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False, index=True)
    feature_summary = Column(JSON, nullable=True)
    explanation = Column(JSON, nullable=True)
    detected_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    normalized_event = relationship("NormalizedEvent", backref="anomaly_results")

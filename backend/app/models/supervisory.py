"""
ULPF Phase 7 Supervisory Intelligence SQLAlchemy Data Models.

Provides models for entity assessments, capability dimension evaluations,
supervisory indicators (execution gaps, negative space), review samples,
and audit trails for human review.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class EntityAssessment(Base):
    """Stores high-level supervisory assessment metrics for a CSE or organization entity."""
    __tablename__ = "entity_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(64), nullable=False, index=True)
    entity_name = Column(String(128), nullable=False)
    assessment_period = Column(String(64), nullable=False)  # e.g., "2026-Q3", "Last 30 Days"
    
    overall_score = Column(Float, nullable=False, default=0.0)  # 0.0 to 100.0
    detection_score = Column(Float, nullable=False, default=0.0)
    investigation_score = Column(Float, nullable=False, default=0.0)
    escalation_score = Column(Float, nullable=False, default=0.0)
    operational_discipline_score = Column(Float, nullable=False, default=0.0)
    monitoring_coverage_score = Column(Float, nullable=False, default=0.0)
    data_quality_score = Column(Float, nullable=False, default=0.0)
    cyber_resilience_indicator = Column(Float, nullable=False, default=0.0)
    
    confidence = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    risk_category = Column(String(32), nullable=False, default="INSUFFICIENT_EVIDENCE", index=True)
    trend = Column(String(32), nullable=False, default="INSUFFICIENT_EVIDENCE")
    
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    capabilities = relationship("CapabilityAssessment", back_populates="entity_assessment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_entity_assessments_entity_period", "entity_id", "assessment_period"),
    )


class CapabilityAssessment(Base):
    """Detailed score and evidence breakdown for one of the 8 supervisory capability dimensions."""
    __tablename__ = "capability_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("entity_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    capability_name = Column(String(64), nullable=False, index=True)
    # Dimension name: Threat Detection, Investigation, Escalation, Incident Response,
    # Security Operations, Governance & Oversight, Operational Discipline, Cyber Resilience
    
    score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)
    indicators = Column(JSON, nullable=False, default=list)
    positive_signals = Column(JSON, nullable=False, default=list)
    negative_signals = Column(JSON, nullable=False, default=list)
    supporting_evidence = Column(JSON, nullable=False, default=dict)
    explanation = Column(Text, nullable=False, default="")

    entity_assessment = relationship("EntityAssessment", back_populates="capabilities")


class SupervisoryIndicator(Base):
    """Supervisory finding (execution gap, negative space, baseline deviation, correlation)."""
    __tablename__ = "supervisory_indicators"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(64), nullable=False, index=True)
    indicator_type = Column(String(64), nullable=False, index=True)
    # Types: EXECUTION_GAP, NEGATIVE_SPACE, DEVIATION, CORRELATION
    
    title = Column(String(255), nullable=False)
    severity = Column(String(32), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    time_period = Column(String(64), nullable=False)
    
    evidence = Column(JSON, nullable=False, default=dict)
    explanation = Column(Text, nullable=False)
    recommended_manual_review = Column(Text, nullable=False)
    
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    # Status: OPEN, UNDER_REVIEW, CONFIRMED, DISMISSED, INSUFFICIENT_EVIDENCE
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    reviews = relationship("SupervisoryReview", back_populates="indicator", cascade="all, delete-orphan")


class ReviewSample(Base):
    """Prioritized alert/event review sample for supervisory sampling."""
    __tablename__ = "review_samples"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(64), nullable=False, index=True)
    event_id = Column(String(64), nullable=False, index=True)
    raw_event_id = Column(String(64), nullable=False, index=True)
    
    priority_label = Column(String(32), nullable=False, index=True)
    # Priority: PRIORITY 1, PRIORITY 2, PRIORITY 3, ROUTINE
    priority_score = Column(Float, nullable=False, default=0.0)
    
    reasons = Column(JSON, nullable=False, default=list)
    capability_tags = Column(JSON, nullable=False, default=list)
    
    severity = Column(String(32), nullable=False)
    anomaly_score = Column(Float, nullable=False, default=0.0)
    closure_time_seconds = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SupervisoryReview(Base):
    """Audit log of human examiner review decisions on supervisory indicators."""
    __tablename__ = "supervisory_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    indicator_id = Column(String(36), ForeignKey("supervisory_indicators.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer = Column(String(128), nullable=False)
    previous_status = Column(String(32), nullable=False)
    decision = Column(String(32), nullable=False)
    notes = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    indicator = relationship("SupervisoryIndicator", back_populates="reviews")

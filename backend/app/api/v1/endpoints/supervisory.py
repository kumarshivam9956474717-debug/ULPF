"""
ULPF Phase 7 Supervisory Intelligence REST API Endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.supervisory import SupervisoryService, EvidenceChainEngine
from app.services.supervisory.models import (
    EntityAssessmentResponse,
    ReviewSubmissionRequest,
    ReviewAuditDTO,
    EvidenceChainDTO,
)
from app.models.supervisory import SupervisoryIndicator, ReviewSample

router = APIRouter()
service = SupervisoryService()
evidence_engine = EvidenceChainEngine()


@router.get("/entities")
def get_entities(db: Session = Depends(get_db)):
    """List registered CSEs/entities available for supervisory assessment."""
    return [
        {"entity_id": "CSE-ALPHA-01", "entity_name": "Perimeter Command Gateway Alpha", "status": "ACTIVE"},
        {"entity_id": "CSE-BETA-02", "entity_name": "Regional Hub Beta", "status": "ACTIVE"},
        {"entity_id": "CSE-GAMMA-03", "entity_name": "Data Center Node Gamma", "status": "ACTIVE"},
    ]


@router.get("/entities/{entity_id}")
def get_entity_by_id(entity_id: str, db: Session = Depends(get_db)):
    """Get entity details and status."""
    return {
        "entity_id": entity_id,
        "entity_name": f"Organization CSE {entity_id}",
        "status": "ACTIVE",
        "monitoring_coverage": "FULL",
        "registered_sources_count": 3,
    }


@router.get("/assessment/{entity_id}", response_model=EntityAssessmentResponse)
def get_entity_assessment(
    entity_id: str,
    period: str = Query("Current Window", description="Assessment period"),
    db: Session = Depends(get_db),
):
    """Retrieve comprehensive supervisory assessment for an entity."""
    return service.run_entity_assessment(db, entity_id=entity_id, period=period)


@router.post("/analyze", response_model=EntityAssessmentResponse)
def run_supervisory_analysis(
    entity_id: str = Query("CSE-ALPHA-01"),
    period: str = Query("Current Window"),
    db: Session = Depends(get_db),
):
    """Trigger on-demand multi-dimensional supervisory intelligence scan for an entity."""
    return service.run_entity_assessment(db, entity_id=entity_id, period=period)


@router.get("/indicators")
def get_supervisory_indicators(
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List supervisory findings and execution gap indicators."""
    query = db.query(SupervisoryIndicator)
    if entity_id:
        query = query.filter(SupervisoryIndicator.entity_id == entity_id)
    if status:
        query = query.filter(SupervisoryIndicator.status == status)

    indicators = query.order_by(SupervisoryIndicator.created_at.desc()).all()
    return [
        {
            "id": ind.id,
            "entity_id": ind.entity_id,
            "indicator_type": ind.indicator_type,
            "title": ind.title,
            "severity": ind.severity,
            "confidence": ind.confidence,
            "time_period": ind.time_period,
            "evidence": ind.evidence,
            "explanation": ind.explanation,
            "recommended_manual_review": ind.recommended_manual_review,
            "status": ind.status,
            "created_at": ind.created_at.isoformat() if ind.created_at else None,
        }
        for ind in indicators
    ]


@router.get("/samples")
def get_prioritized_review_samples(
    entity_id: str = Query("CSE-ALPHA-01"),
    priority_label: Optional[str] = Query(None, description="PRIORITY 1, PRIORITY 2, PRIORITY 3, ROUTINE"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve prioritized alert samples for supervisory review."""
    query = db.query(ReviewSample).filter(ReviewSample.entity_id == entity_id)
    if priority_label:
        query = query.filter(ReviewSample.priority_label == priority_label)

    samples = query.order_by(ReviewSample.priority_score.desc()).limit(limit).all()
    if not samples:
        # Generate fresh sample set if none in DB
        resp = service.run_entity_assessment(db, entity_id=entity_id)
        return resp.priority_samples[:limit]

    return [
        {
            "id": s.id,
            "entity_id": s.entity_id,
            "event_id": s.event_id,
            "raw_event_id": s.raw_event_id,
            "priority_label": s.priority_label,
            "priority_score": s.priority_score,
            "reasons": s.reasons,
            "capability_tags": s.capability_tags,
            "severity": s.severity,
            "anomaly_score": s.anomaly_score,
            "closure_time_seconds": s.closure_time_seconds,
            "timestamp": s.created_at.isoformat() if s.created_at else None,
        }
        for s in samples
    ]


@router.get("/peer-comparison")
def get_peer_comparison(
    entity_id: str = Query("CSE-ALPHA-01"),
    peer_group: str = Query("All CSE Peers"),
    db: Session = Depends(get_db),
):
    """Retrieve entity vs peer benchmark comparison matrix."""
    resp = service.run_entity_assessment(db, entity_id=entity_id)
    return resp.peer_benchmarking


@router.get("/trends")
def get_supervisory_trends(
    entity_id: str = Query("CSE-ALPHA-01"),
    db: Session = Depends(get_db),
):
    """Retrieve period-over-period trend analysis."""
    resp = service.run_entity_assessment(db, entity_id=entity_id)
    return resp.trend_analysis


@router.get("/evidence/{finding_id}", response_model=EvidenceChainDTO)
def get_finding_evidence_chain(
    finding_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve 6-level evidence chain (Finding -> Indicator -> Metrics -> Normalized Event -> Raw Event -> SHA-256)."""
    chain = evidence_engine.build_evidence_chain(db, finding_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Supervisory finding '{finding_id}' not found")
    return chain


@router.post("/review/{finding_id}", response_model=ReviewAuditDTO)
def submit_human_review(
    finding_id: str,
    submission: ReviewSubmissionRequest,
    db: Session = Depends(get_db),
):
    """Submit human examiner review status update and notes for a supervisory finding."""
    try:
        return service.review_indicator(db, finding_id, submission)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report")
@router.post("/report")
def export_supervisory_report(
    entity_id: str = Query("CSE-ALPHA-01"),
    format_type: str = Query("json", description="json or csv"),
    db: Session = Depends(get_db),
):
    """Download supervisory assessment report distinguishing SYSTEM-GENERATED ANALYTICS from HUMAN CONCLUSIONS."""
    content = service.generate_report(db, entity_id=entity_id, format_type=format_type)
    media_type = "text/csv" if format_type.lower() == "csv" else "application/json"
    filename = f"supervisory_report_{entity_id}.csv" if format_type.lower() == "csv" else f"supervisory_report_{entity_id}.json"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

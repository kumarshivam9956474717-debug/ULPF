from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.security_analytics.models import (
    SecurityOverview,
    SourceHealthMetrics,
    CoverageFindingItem,
    CorrelationGroup,
    FindingResponse,
    AnalyzeRunResponse
)
from app.services.security_analytics.service import security_analytics_service

router = APIRouter()


@router.get(
    "/overview",
    response_model=SecurityOverview,
    summary="Get security event analytics overview",
    description="Returns high-level event counts, source health counts, findings metrics, and overall data quality index."
)
def get_security_overview(db: Session = Depends(get_db)) -> SecurityOverview:
    try:
        return security_analytics_service.get_overview(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch security overview: {str(exc)}"
        )


@router.get(
    "/trends",
    summary="Get event volume and anomaly trends",
    description="Returns time-bucketed event and anomaly trend data over specified timeframe (24h, 7d, 30d)."
)
def get_security_trends(
    timeframe: str = Query("24h", description="Timeframe window (24h, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    try:
        return security_analytics_service.get_trends(db, timeframe=timeframe)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch security trends: {str(exc)}"
        )


@router.get(
    "/sources",
    response_model=List[SourceHealthMetrics],
    summary="Get source-level health analytics",
    description="Evaluates all registered log sources and returns status (HEALTHY, DEGRADED, SUSPICIOUS, INACTIVE) with event rates and error metrics."
)
def get_sources_health(db: Session = Depends(get_db)) -> List[SourceHealthMetrics]:
    try:
        return security_analytics_service.get_sources_health(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sources health: {str(exc)}"
        )


@router.get(
    "/coverage",
    response_model=List[CoverageFindingItem],
    summary="Get negative-space & monitoring gap analysis",
    description="Identifies potential monitoring gaps, telemetry reductions, missing category/severity windows, and unmonitored assets."
)
def get_coverage_gaps(db: Session = Depends(get_db)) -> List[CoverageFindingItem]:
    try:
        return security_analytics_service.get_coverage_gaps(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze coverage gaps: {str(exc)}"
        )


@router.get(
    "/baselines",
    summary="Get source historical baselines and deviations",
    description="Returns 14-day historical volume/distribution baselines and current z-score deviations."
)
def get_source_baselines(db: Session = Depends(get_db)):
    try:
        return security_analytics_service.get_baselines(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch source baselines: {str(exc)}"
        )


@router.get(
    "/correlations",
    response_model=List[CorrelationGroup],
    summary="Get cross-source correlation candidates",
    description="Scans normalized events for multi-source event clusters matching on IP, asset, user, or port within configurable time windows."
)
def get_correlation_candidates(
    window_minutes: int = Query(15, description="Time window in minutes"),
    db: Session = Depends(get_db)
) -> List[CorrelationGroup]:
    try:
        return security_analytics_service.get_correlations(db, window_minutes=window_minutes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan correlations: {str(exc)}"
        )


@router.post(
    "/analyze",
    response_model=AnalyzeRunResponse,
    summary="Trigger on-demand security analytics scan",
    description="Executes a full security analytics scan updating source health, baselines, coverage gaps, correlations, and supervisory findings."
)
def run_security_analysis(db: Session = Depends(get_db)) -> AnalyzeRunResponse:
    try:
        return security_analytics_service.run_analysis_scan(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security analysis scan failed: {str(exc)}"
        )


@router.get(
    "/findings",
    response_model=List[FindingResponse],
    summary="Get list of supervisory security findings",
    description="Returns paginated supervisory findings ordered by priority score with optional status, finding_type, severity, or source filters."
)
def list_findings(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, REVIEWED, DISMISSED)"),
    finding_type: Optional[str] = Query(None, description="Filter by finding type"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> List[FindingResponse]:
    try:
        return security_analytics_service.list_findings(
            db=db,
            status=status,
            finding_type=finding_type,
            severity=severity,
            source_id=source_id,
            limit=limit,
            offset=offset
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch findings: {str(exc)}"
        )


@router.get(
    "/findings/report",
    summary="Get supervisory findings report data",
    description="Returns structured security analytics findings report with analytical methodology, disclaimer, and prioritized findings."
)
@router.get(
    "/report",
    summary="Get supervisory findings report data alias"
)
def get_findings_report(db: Session = Depends(get_db)):
    try:
        return security_analytics_service.get_findings_report_data(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch findings report data: {str(exc)}"
        )


@router.get(
    "/findings/export",
    summary="Export supervisory findings report",
    description="Exports security analytics findings in JSON or CSV format."
)
def export_findings(
    format: str = Query("json", description="Export format (json or csv)"),
    db: Session = Depends(get_db)
):
    try:
        content, media_type = security_analytics_service.export_findings(db, export_format=format)
        filename = f"ulpf_security_findings_{format}.{format}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export findings: {str(exc)}"
        )


@router.get(
    "/findings/{finding_id}",
    response_model=FindingResponse,
    summary="Get detailed supervisory finding by ID"
)
def get_finding_by_id(
    finding_id: str,
    db: Session = Depends(get_db)
) -> FindingResponse:
    finding = security_analytics_service.get_finding(db, finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found."
        )
    return finding


@router.post(
    "/findings/{finding_id}/review",
    response_model=FindingResponse,
    summary="Mark finding as REVIEWED"
)
def review_finding(
    finding_id: str,
    actor: str = Query("analyst"),
    db: Session = Depends(get_db)
) -> FindingResponse:
    try:
        return security_analytics_service.review_finding(db, finding_id, actor=actor)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review finding: {str(exc)}"
        )


@router.post(
    "/findings/{finding_id}/dismiss",
    response_model=FindingResponse,
    summary="Mark finding as DISMISSED"
)
def dismiss_finding(
    finding_id: str,
    actor: str = Query("analyst"),
    db: Session = Depends(get_db)
) -> FindingResponse:
    try:
        return security_analytics_service.dismiss_finding(db, finding_id, actor=actor)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss finding: {str(exc)}"
        )

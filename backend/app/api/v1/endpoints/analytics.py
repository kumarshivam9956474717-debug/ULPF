from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_roles
from app.models.user import User
from app.services.export.models import ExportRequest, ExportMetrics, ExportStatus
from app.services.export.export_service import export_service
from app.services.analytics.models import (
    OverviewMetrics,
    TimelinePoint,
    DistributionItem,
    TopItem,
    AnalyticsFilter
)
from app.services.analytics.service import analytics_service

router = APIRouter()


# ---------------- Parquet Export ----------------

@router.post("/export", response_model=ExportMetrics, summary="Export normalized events to Apache Parquet")
def trigger_parquet_export(
    request: ExportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN"))
):
    """
    Exports normalized UES events from PostgreSQL into partitioned Apache Parquet files
    (year=YYYY/month=MM/day=DD) with chunked database extraction.
    """
    try:
        metrics = export_service.export_events(
            db=db,
            format=request.format,
            start_time=request.start_time,
            end_time=request.end_time,
            source_id=request.source_id,
            batch_size=request.batch_size
        )
        return metrics
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parquet export failed: {str(exc)}"
        )


@router.get("/export/status", response_model=ExportStatus, summary="Get latest Parquet export status and telemetry")
def get_export_status(
    _: User = Depends(require_roles("ADMIN", "ANALYST", "OPERATOR", "VIEWER"))
):
    """Returns telemetry from the most recent Parquet export operation."""
    return export_service.get_status()


# ---------------- Aggregations ----------------

def _build_filter(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    vendor: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    _: User = Depends(require_roles("ADMIN", "ANALYST", "OPERATOR", "VIEWER"))
) -> AnalyticsFilter:
    return AnalyticsFilter(
        start_time=start_time,
        end_time=end_time,
        vendor=vendor,
        severity=severity,
        device_type=device_type
    )


@router.get("/overview", response_model=OverviewMetrics, summary="Overview telemetry & throughput metrics")
def get_overview(
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns total event counts, failure counts, anomaly counts, and processing rates."""
    return analytics_service.get_overview(db, filters)


@router.get("/timeline", response_model=List[TimelinePoint], summary="Event count timeline")
def get_timeline(
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns hourly time-bucketed event counts."""
    return analytics_service.get_timeline(db, filters)


@router.get("/vendors", response_model=List[DistributionItem], summary="Vendor distribution")
def get_vendors(
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns event counts grouped by security vendor."""
    return analytics_service.get_vendors(db, filters)


@router.get("/severity", response_model=List[DistributionItem], summary="Severity distribution")
def get_severity(
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns event counts grouped by severity level."""
    return analytics_service.get_severity(db, filters)


@router.get("/categories", response_model=List[DistributionItem], summary="Event category distribution")
def get_categories(
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns event counts grouped by event category."""
    return analytics_service.get_categories(db, filters)


@router.get("/top-ips", response_model=List[TopItem], summary="Top source IP addresses")
def get_top_source_ips(
    limit: int = Query(10, ge=1, le=100),
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns top active source IP addresses."""
    return analytics_service.get_top_source_ips(db, limit, filters)


@router.get("/top-ports", response_model=List[TopItem], summary="Top destination ports")
def get_top_destination_ports(
    limit: int = Query(10, ge=1, le=100),
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns top targeted destination ports."""
    return analytics_service.get_top_destination_ports(db, limit, filters)


@router.get("/sources", response_model=List[DistributionItem], summary="Device type distribution")
def get_sources(
    filters: AnalyticsFilter = Depends(_build_filter),
    db: Session = Depends(get_db)
):
    """Returns event counts grouped by perimeter device type."""
    return analytics_service.get_sources(db, filters)

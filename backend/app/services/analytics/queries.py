from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.models.validation_result import ValidationResult
from app.models.processing_run import ProcessingRun
from app.models.anomaly_result import AnomalyResult
from app.services.analytics.models import (
    OverviewMetrics,
    TimelinePoint,
    DistributionItem,
    TopItem,
    AnalyticsFilter
)


def _apply_filters(query, model, filters: Optional[AnalyticsFilter] = None):
    if not filters:
        return query
    if filters.start_time and hasattr(model, "timestamp"):
        query = query.filter(model.timestamp >= filters.start_time)
    if filters.end_time and hasattr(model, "timestamp"):
        query = query.filter(model.timestamp <= filters.end_time)
    if filters.vendor and hasattr(model, "vendor"):
        query = query.filter(model.vendor == filters.vendor)
    if filters.severity and hasattr(model, "severity"):
        query = query.filter(model.severity == filters.severity)
    if filters.device_type and hasattr(model, "device_type"):
        query = query.filter(model.device_type == filters.device_type)
    return query


def query_overview(db: Session, filters: Optional[AnalyticsFilter] = None) -> OverviewMetrics:
    """Calculates high-level telemetry and event processing rates."""
    norm_q = _apply_filters(db.query(func.count(NormalizedEvent.id)), NormalizedEvent, filters)
    total_events = norm_q.scalar() or 0

    raw_q = db.query(func.count(RawEvent.id))
    if filters and filters.start_time:
        raw_q = raw_q.filter(RawEvent.received_at >= filters.start_time)
    if filters and filters.end_time:
        raw_q = raw_q.filter(RawEvent.received_at <= filters.end_time)
    total_raw = raw_q.scalar() or 0

    # Validation failures
    val_q = db.query(func.count(ValidationResult.id)).filter(ValidationResult.validation_status == "invalid")
    if filters and filters.start_time:
        val_q = val_q.filter(ValidationResult.validation_timestamp >= filters.start_time)
    if filters and filters.end_time:
        val_q = val_q.filter(ValidationResult.validation_timestamp <= filters.end_time)
    validation_failures = val_q.scalar() or 0

    # Parser/Run failures
    run_q = db.query(func.coalesce(func.sum(ProcessingRun.records_failed), 0))
    if filters and filters.start_time:
        run_q = run_q.filter(ProcessingRun.started_at >= filters.start_time)
    if filters and filters.end_time:
        run_q = run_q.filter(ProcessingRun.started_at <= filters.end_time)
    parser_failures = int(run_q.scalar() or 0)

    # Anomaly count
    anomaly_q = db.query(func.count(AnomalyResult.id)).filter(AnomalyResult.is_anomaly == True)
    if filters and filters.start_time:
        anomaly_q = anomaly_q.filter(AnomalyResult.detected_at >= filters.start_time)
    if filters and filters.end_time:
        anomaly_q = anomaly_q.filter(AnomalyResult.detected_at <= filters.end_time)
    anomaly_count = anomaly_q.scalar() or 0

    # Rate calculation
    min_ts_q = _apply_filters(db.query(func.min(NormalizedEvent.timestamp)), NormalizedEvent, filters)
    max_ts_q = _apply_filters(db.query(func.max(NormalizedEvent.timestamp)), NormalizedEvent, filters)
    min_ts = min_ts_q.scalar()
    max_ts = max_ts_q.scalar()

    epm = 0.0
    eph = 0.0
    if min_ts and max_ts and total_events > 0:
        duration_minutes = max((max_ts - min_ts).total_seconds() / 60.0, 1.0)
        epm = round(total_events / duration_minutes, 2)
        eph = round(epm * 60.0, 2)
    elif total_events > 0:
        epm = float(total_events)
        eph = float(total_events * 60)

    return OverviewMetrics(
        total_events=total_events,
        total_raw_events=total_raw,
        events_per_minute=epm,
        events_per_hour=eph,
        validation_failures=validation_failures,
        parser_failures=parser_failures,
        anomaly_count=anomaly_count
    )


def query_timeline(db: Session, filters: Optional[AnalyticsFilter] = None) -> List[TimelinePoint]:
    """Generates hourly time-bucketed event counts."""
    is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else False

    if is_sqlite:
        bucket = func.strftime("%Y-%m-%d %H:00:00", NormalizedEvent.timestamp)
    else:
        bucket = func.to_char(func.date_trunc("hour", NormalizedEvent.timestamp), "YYYY-MM-DD HH24:00:00")

    q = db.query(
        bucket.label("time_bucket"),
        func.count(NormalizedEvent.id).label("cnt")
    ).filter(NormalizedEvent.timestamp != None)

    q = _apply_filters(q, NormalizedEvent, filters)
    rows = q.group_by("time_bucket").order_by("time_bucket").all()

    points = []
    for r in rows:
        points.append(TimelinePoint(
            timestamp=str(r[0]),
            count=r[1],
            errors=0
        ))
    return points


def query_distribution(db: Session, column, filters: Optional[AnalyticsFilter] = None) -> List[DistributionItem]:
    """Generic distribution query for categorized fields (vendor, severity, category)."""
    total_q = _apply_filters(db.query(func.count(NormalizedEvent.id)), NormalizedEvent, filters)
    total_count = total_q.scalar() or 0

    col_val = func.coalesce(column, "unknown")
    q = db.query(
        col_val.label("grp"),
        func.count(NormalizedEvent.id).label("cnt")
    )
    q = _apply_filters(q, NormalizedEvent, filters)
    rows = q.group_by("grp").order_by(desc("cnt")).all()

    items = []
    for r in rows:
        key_str = str(r[0])
        count_val = r[1]
        pct = round((count_val / total_count * 100), 2) if total_count > 0 else 0.0
        items.append(DistributionItem(key=key_str, count=count_val, percentage=pct))
    return items


def query_top_items(db: Session, column, limit: int = 10, filters: Optional[AnalyticsFilter] = None) -> List[TopItem]:
    """Generic ranking query for top entities (top source IPs, top destination ports)."""
    total_q = _apply_filters(db.query(func.count(NormalizedEvent.id)), NormalizedEvent, filters)
    total_count = total_q.scalar() or 0

    q = db.query(
        column.label("item_val"),
        func.count(NormalizedEvent.id).label("cnt")
    ).filter(column != None)
    q = _apply_filters(q, NormalizedEvent, filters)
    rows = q.group_by("item_val").order_by(desc("cnt")).limit(limit).all()

    items = []
    for r in rows:
        val_str = str(r[0])
        count_val = r[1]
        pct = round((count_val / total_count * 100), 2) if total_count > 0 else 0.0
        items.append(TopItem(item=val_str, count=count_val, percentage=pct))
    return items

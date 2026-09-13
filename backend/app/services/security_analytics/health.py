from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.log_source import LogSource
from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.models.validation_result import ValidationResult
from app.models.anomaly_result import AnomalyResult
from app.models.processing_run import ProcessingRun
from app.services.security_analytics.models import SourceHealthMetrics, HealthStatus


def _ensure_tz_datetime(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except Exception:
            return None
    if hasattr(val, "tzinfo") and val.tzinfo is not None:
        return val
    return val.replace(tzinfo=timezone.utc)


class SourceHealthAnalyzer:
    """
    Evaluates source-level health analytics and classifies source status into
    HEALTHY, DEGRADED, SUSPICIOUS, or INACTIVE using deterministic heuristic rules.
    """

    # Health Thresholds
    GAP_INACTIVE_MINUTES = 120.0    # No events for >2h -> INACTIVE
    GAP_DEGRADED_MINUTES = 30.0     # No events for >30m -> DEGRADED
    PARSING_SUCCESS_DEGRADED_PCT = 85.0   # Success rate < 85% -> DEGRADED
    VALIDATION_FAILURE_DEGRADED_PCT = 15.0 # Validation failure > 15% -> DEGRADED
    ANOMALY_RATE_SUSPICIOUS_PCT = 15.0     # Anomaly rate > 15% -> SUSPICIOUS
    UNKNOWN_FORMAT_SUSPICIOUS_PCT = 20.0   # Unknown format rate > 20% -> SUSPICIOUS

    @classmethod
    def analyze_source_health(cls, db: Session, source: LogSource, now_dt: Optional[datetime] = None) -> SourceHealthMetrics:
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)

        sid = source.source_id

        # 1. Total Raw & Normalized Events for this source
        total_raw = db.query(func.count(RawEvent.id)).filter(RawEvent.source_id == sid).scalar() or 0
        total_norm = db.query(func.count(NormalizedEvent.id)).filter(NormalizedEvent.source_id == sid).scalar() if hasattr(NormalizedEvent, "source_id") else 0
        
        # If NormalizedEvent doesn't have source_id column, match via RawEvent relationship or vendor
        if total_norm == 0 and total_raw > 0:
            total_norm = (
                db.query(func.count(NormalizedEvent.id))
                .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
                .filter(RawEvent.source_id == sid)
                .scalar() or 0
            )

        # 2. Last Event Timestamp
        last_raw_ts = db.query(func.max(RawEvent.received_at)).filter(RawEvent.source_id == sid).scalar()
        last_norm_ts = None
        if total_norm > 0:
            last_norm_ts = (
                db.query(func.max(NormalizedEvent.timestamp))
                .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
                .filter(RawEvent.source_id == sid)
                .scalar()
            )

        last_seen = _ensure_tz_datetime(last_raw_ts or last_norm_ts)

        # Ingestion gap duration (minutes)
        gap_mins = 0.0
        if last_seen:
            gap_mins = max(0.0, (now_dt - last_seen).total_seconds() / 60.0)
        else:
            gap_mins = 999999.0  # Never seen

        # 3. Processing Runs & Parsing Success Rate
        run_stats = (
            db.query(
                func.coalesce(func.sum(ProcessingRun.records_received), 0),
                func.coalesce(func.sum(ProcessingRun.records_parsed), 0),
                func.coalesce(func.sum(ProcessingRun.records_failed), 0)
            )
            .filter(ProcessingRun.source_id == sid)
            .first()
        )
        rec_rcvd, rec_parsed, rec_failed = run_stats if run_stats else (0, 0, 0)

        parsing_success_rate = 100.0
        if rec_rcvd > 0:
            parsing_success_rate = round((rec_parsed / rec_rcvd) * 100.0, 1)
        elif total_raw > 0:
            parsing_success_rate = round((total_norm / total_raw) * 100.0, 1)

        # 4. Validation Failure Rate
        val_failures = (
            db.query(func.count(ValidationResult.id))
            .join(NormalizedEvent, ValidationResult.normalized_event_id == NormalizedEvent.event_id)
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == sid, ValidationResult.validation_status == "invalid")
            .scalar() or 0
        )
        val_failure_rate = round((val_failures / total_norm * 100.0), 1) if total_norm > 0 else 0.0

        # 5. Anomaly Rate
        anom_count = (
            db.query(func.count(AnomalyResult.id))
            .join(NormalizedEvent, AnomalyResult.event_id == NormalizedEvent.event_id)
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == sid, AnomalyResult.is_anomaly == True)
            .scalar() or 0
        )
        anomaly_rate = round((anom_count / total_norm * 100.0), 1) if total_norm > 0 else 0.0

        # 6. Unknown Format Rate
        unknown_format_count = (
            db.query(func.count(RawEvent.id))
            .filter(RawEvent.source_id == sid, RawEvent.source_format == "unknown")
            .scalar() or 0
        )
        unknown_format_rate = round((unknown_format_count / total_raw * 100.0), 1) if total_raw > 0 else 0.0

        # 7. Events per Hour Calculation
        first_raw_ts_raw = db.query(func.min(RawEvent.received_at)).filter(RawEvent.source_id == sid).scalar()
        first_raw_ts = _ensure_tz_datetime(first_raw_ts_raw)
        eph = 0.0
        if first_raw_ts and last_seen and total_raw > 0:
            active_hours = max((last_seen - first_raw_ts).total_seconds() / 3600.0, 1.0)
            eph = round(total_raw / active_hours, 1)
        elif total_raw > 0:
            eph = float(total_raw)

        # 8. Deterministic Health Classification
        status = HealthStatus.HEALTHY
        reasons = []

        if total_raw == 0 or gap_mins >= cls.GAP_INACTIVE_MINUTES:
            status = HealthStatus.INACTIVE
            if total_raw == 0:
                reasons.append("Source registered but zero log records received.")
            else:
                reasons.append(f"No events received for past {gap_mins:.1f} minutes.")
        elif anomaly_rate >= cls.ANOMALY_RATE_SUSPICIOUS_PCT or unknown_format_rate >= cls.UNKNOWN_FORMAT_SUSPICIOUS_PCT:
            status = HealthStatus.SUSPICIOUS
            if anomaly_rate >= cls.ANOMALY_RATE_SUSPICIOUS_PCT:
                reasons.append(f"High statistical anomaly rate ({anomaly_rate}%).")
            if unknown_format_rate >= cls.UNKNOWN_FORMAT_SUSPICIOUS_PCT:
                reasons.append(f"High unknown-format rate ({unknown_format_rate}%).")
        elif parsing_success_rate < cls.PARSING_SUCCESS_DEGRADED_PCT or val_failure_rate > cls.VALIDATION_FAILURE_DEGRADED_PCT or gap_mins > cls.GAP_DEGRADED_MINUTES:
            status = HealthStatus.DEGRADED
            if parsing_success_rate < cls.PARSING_SUCCESS_DEGRADED_PCT:
                reasons.append(f"Degraded parsing success rate ({parsing_success_rate}%).")
            if val_failure_rate > cls.VALIDATION_FAILURE_DEGRADED_PCT:
                reasons.append(f"Elevated validation failure rate ({val_failure_rate}%).")
            if gap_mins > cls.GAP_DEGRADED_MINUTES:
                reasons.append(f"Ingestion gap of {gap_mins:.1f} minutes detected.")
        else:
            reasons.append("Telemetry ingestion healthy and operating within normal parameters.")

        return SourceHealthMetrics(
            source_id=sid,
            name=source.hostname or source.source_id,
            vendor=source.vendor or "unknown",
            device_type=source.device_type or "security_device",
            status=status,
            total_events=total_raw,
            events_per_hour=eph,
            avg_hourly_volume=eph,
            last_event_timestamp=last_seen,
            parsing_success_rate=parsing_success_rate,
            validation_failure_rate=val_failure_rate,
            anomaly_rate=anomaly_rate,
            unknown_format_rate=unknown_format_rate,
            ingestion_gap_duration_minutes=round(gap_mins, 1),
            status_reason=" | ".join(reasons)
        )

    @classmethod
    def get_all_sources_health(cls, db: Session) -> List[SourceHealthMetrics]:
        sources = db.query(LogSource).all()
        now_dt = datetime.now(timezone.utc)
        return [cls.analyze_source_health(db, s, now_dt) for s in sources]

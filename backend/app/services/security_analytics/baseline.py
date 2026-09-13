import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.log_source import LogSource
from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.models.security_analytics import SourceBaseline
from app.services.security_analytics.models import BaselineMetrics, BaselineDeviationItem


class BaselineEngine:
    """
    Historical Baseline Engine.
    Computes statistical baselines (mean, median, stddev, distributions) for each source
    and detects volume spikes, volume drops, and distribution shifts using z-scores.
    """

    @classmethod
    def calculate_source_baseline(cls, db: Session, source_id: str) -> SourceBaseline:
        """
        Calculates and persists historical baseline statistics for a log source.
        """
        now_dt = datetime.now(timezone.utc)
        lookback_start = now_dt - timedelta(days=14)

        # 1. Hourly volume bucket aggregation
        is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else False
        if is_sqlite:
            bucket = func.strftime("%Y-%m-%d %H:00:00", NormalizedEvent.timestamp)
        else:
            bucket = func.to_char(func.date_trunc("hour", NormalizedEvent.timestamp), "YYYY-MM-DD HH24:00:00")

        hourly_rows = (
            db.query(
                bucket.label("hour_bucket"),
                func.count(NormalizedEvent.id).label("cnt")
            )
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == source_id, NormalizedEvent.timestamp >= lookback_start)
            .group_by("hour_bucket")
            .all()
        )

        volumes = [r[1] for r in hourly_rows]
        sample_hours = len(volumes)

        avg_vol = 0.0
        median_vol = 0.0
        stddev_vol = 0.0

        if sample_hours > 0:
            avg_vol = float(sum(volumes)) / sample_hours
            sorted_vols = sorted(volumes)
            mid = sample_hours // 2
            if sample_hours % 2 == 0 and sample_hours >= 2:
                median_vol = (sorted_vols[mid - 1] + sorted_vols[mid]) / 2.0
            else:
                median_vol = float(sorted_vols[mid])

            variance = sum((x - avg_vol) ** 2 for x in volumes) / sample_hours
            stddev_vol = math.sqrt(variance)

        # 2. Severity distribution
        total_events = sum(volumes) if volumes else 1
        sev_rows = (
            db.query(NormalizedEvent.severity, func.count(NormalizedEvent.id))
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == source_id, NormalizedEvent.timestamp >= lookback_start)
            .group_by(NormalizedEvent.severity)
            .all()
        )
        sev_dist = {str(r[0] or "unknown").lower(): round((r[1] / total_events) * 100.0, 2) for r in sev_rows}

        # 3. Protocol distribution
        proto_rows = (
            db.query(NormalizedEvent.protocol, func.count(NormalizedEvent.id))
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == source_id, NormalizedEvent.timestamp >= lookback_start)
            .group_by(NormalizedEvent.protocol)
            .all()
        )
        proto_dist = {str(r[0] or "unknown").lower(): round((r[1] / total_events) * 100.0, 2) for r in proto_rows}

        # 4. Action distribution
        act_rows = (
            db.query(NormalizedEvent.action, func.count(NormalizedEvent.id))
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == source_id, NormalizedEvent.timestamp >= lookback_start)
            .group_by(NormalizedEvent.action)
            .all()
        )
        act_dist = {str(r[0] or "unknown").lower(): round((r[1] / total_events) * 100.0, 2) for r in act_rows}

        # Upsert into database
        baseline = db.query(SourceBaseline).filter(SourceBaseline.source_id == source_id).first()
        if not baseline:
            baseline = SourceBaseline(
                source_id=source_id,
                avg_hourly_volume=avg_vol,
                median_hourly_volume=median_vol,
                stddev_hourly_volume=stddev_vol,
                severity_distribution=sev_dist,
                protocol_distribution=proto_dist,
                action_distribution=act_dist,
                sample_hours_count=sample_hours,
                calculated_at=now_dt
            )
            db.add(baseline)
        else:
            baseline.avg_hourly_volume = avg_vol
            baseline.median_hourly_volume = median_vol
            baseline.stddev_hourly_volume = stddev_vol
            baseline.severity_distribution = sev_dist
            baseline.protocol_distribution = proto_dist
            baseline.action_distribution = act_dist
            baseline.sample_hours_count = sample_hours
            baseline.calculated_at = now_dt

        db.commit()
        db.refresh(baseline)
        return baseline

    @classmethod
    def detect_deviations(cls, db: Session, source_id: str, now_dt: Optional[datetime] = None) -> List[BaselineDeviationItem]:
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)

        baseline = db.query(SourceBaseline).filter(SourceBaseline.source_id == source_id).first()
        if not baseline or baseline.avg_hourly_volume == 0.0:
            # Generate baseline if missing
            baseline = cls.calculate_source_baseline(db, source_id)

        if baseline.avg_hourly_volume == 0.0:
            return []

        deviations: List[BaselineDeviationItem] = []
        recent_hour = now_dt - timedelta(hours=1)

        # Current hour volume count
        current_vol = (
            db.query(func.count(NormalizedEvent.id))
            .join(RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id)
            .filter(RawEvent.source_id == source_id, NormalizedEvent.timestamp >= recent_hour)
            .scalar() or 0
        )

        avg_vol = baseline.avg_hourly_volume
        std_vol = max(1.0, baseline.stddev_hourly_volume)
        z_score = round((current_vol - avg_vol) / std_vol, 2)
        pct_diff = round(((current_vol - avg_vol) / avg_vol) * 100.0, 1)

        # 1. Volume Spike (z-score >= +2.0 or +100% volume surge)
        if z_score >= 2.0 or pct_diff >= 100.0:
            deviations.append(BaselineDeviationItem(
                source_id=source_id,
                deviation_type="VOLUME_SPIKE",
                baseline_value=round(avg_vol, 1),
                current_value=float(current_vol),
                deviation_percentage=pct_diff,
                z_score=z_score,
                explanation=f"Hourly volume ({current_vol}) is +{pct_diff}% above 14-day baseline ({avg_vol:.1f}) (z-score: +{z_score})."
            ))

        # 2. Volume Drop (z-score <= -2.0 or <= -50% drop when expected > 10 events)
        elif z_score <= -2.0 or (pct_diff <= -50.0 and avg_vol >= 10.0):
            deviations.append(BaselineDeviationItem(
                source_id=source_id,
                deviation_type="VOLUME_DROP",
                baseline_value=round(avg_vol, 1),
                current_value=float(current_vol),
                deviation_percentage=pct_diff,
                z_score=z_score,
                explanation=f"Hourly volume ({current_vol}) is {pct_diff}% below 14-day baseline ({avg_vol:.1f}) (z-score: {z_score}). Potential telemetry reduction."
            ))

        return deviations

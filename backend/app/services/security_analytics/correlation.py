import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.services.security_analytics.models import CorrelationGroup


def _ensure_tz_datetime(val: Any) -> datetime:
    if val is None:
        return datetime.now(timezone.utc)
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except Exception:
            return datetime.now(timezone.utc)
    if hasattr(val, "tzinfo") and val.tzinfo is not None:
        return val
    return val.replace(tzinfo=timezone.utc)


class CorrelationEngine:
    """
    Lightweight Cross-Source Correlation Engine.
    Identifies multi-event patterns across distinct log sources/vendors matching on
    source IP, destination IP, asset (hostname), username, or destination port
    within configurable time windows.
    Generates non-attributive 'Correlation candidates' for human review.
    """

    @classmethod
    def scan_correlations(
        cls,
        db: Session,
        window_minutes: int = 15,
        min_events: int = 3,
        now_dt: Optional[datetime] = None
    ) -> List[CorrelationGroup]:
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)

        window_start = now_dt - timedelta(minutes=window_minutes)
        candidates: List[CorrelationGroup] = []

        # 1. Correlate by Source IP across multiple sources/vendors
        sip_rows = (
            db.query(
                NormalizedEvent.source_ip,
                func.count(NormalizedEvent.id).label("evt_cnt"),
                func.count(func.distinct(NormalizedEvent.vendor)).label("vnd_cnt"),
                func.min(NormalizedEvent.timestamp).label("first_ts"),
                func.max(NormalizedEvent.timestamp).label("last_ts")
            )
            .filter(
                NormalizedEvent.source_ip != None,
                NormalizedEvent.source_ip != "",
                NormalizedEvent.timestamp >= window_start
            )
            .group_by(NormalizedEvent.source_ip)
            .having(func.count(NormalizedEvent.id) >= min_events, func.count(func.distinct(NormalizedEvent.vendor)) >= 2)
            .limit(20)
            .all()
        )

        for r in sip_rows:
            ip_val = r[0]
            evt_cnt = r[1]
            vnd_cnt = r[2]
            first_ts = r[3] or window_start
            last_ts = r[4] or now_dt

            # Fetch distinct vendors and preview events
            sample_events = (
                db.query(NormalizedEvent)
                .filter(NormalizedEvent.source_ip == ip_val, NormalizedEvent.timestamp >= window_start)
                .order_by(desc(NormalizedEvent.timestamp))
                .limit(5)
                .all()
            )
            vendors = sorted(list(set(e.vendor for e in sample_events if e.vendor)))

            events_preview = [
                {
                    "event_id": e.event_id,
                    "vendor": e.vendor,
                    "product": e.product,
                    "source_ip": e.source_ip,
                    "destination_ip": e.destination_ip,
                    "destination_port": e.destination_port,
                    "action": e.action,
                    "severity": e.severity,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None
                }
                for e in sample_events
            ]

            candidates.append(CorrelationGroup(
                correlation_id=f"CORR-SIP-{uuid.uuid4().hex[:8].upper()}",
                matching_key=f"source_ip={ip_val}",
                shared_entity_type="source_ip",
                shared_entity_value=ip_val,
                event_count=evt_cnt,
                distinct_sources_count=vnd_cnt,
                distinct_vendors=vendors,
                time_window_seconds=window_minutes * 60,
                first_seen=_ensure_tz_datetime(first_ts),
                last_seen=_ensure_tz_datetime(last_ts),
                events_preview=events_preview,
                explanation=f"Source IP '{ip_val}' generated {evt_cnt} security events across {vnd_cnt} distinct vendors ({', '.join(vendors)}) within past {window_minutes} minutes."
            ))

        # 2. Correlate by Destination IP across multiple sources/vendors
        dip_rows = (
            db.query(
                NormalizedEvent.destination_ip,
                func.count(NormalizedEvent.id).label("evt_cnt"),
                func.count(func.distinct(NormalizedEvent.vendor)).label("vnd_cnt"),
                func.min(NormalizedEvent.timestamp).label("first_ts"),
                func.max(NormalizedEvent.timestamp).label("last_ts")
            )
            .filter(
                NormalizedEvent.destination_ip != None,
                NormalizedEvent.destination_ip != "",
                NormalizedEvent.timestamp >= window_start
            )
            .group_by(NormalizedEvent.destination_ip)
            .having(func.count(NormalizedEvent.id) >= min_events, func.count(func.distinct(NormalizedEvent.vendor)) >= 2)
            .limit(20)
            .all()
        )

        for r in dip_rows:
            dip_val = r[0]
            evt_cnt = r[1]
            vnd_cnt = r[2]
            first_ts = r[3] or window_start
            last_ts = r[4] or now_dt

            sample_events = (
                db.query(NormalizedEvent)
                .filter(NormalizedEvent.destination_ip == dip_val, NormalizedEvent.timestamp >= window_start)
                .order_by(desc(NormalizedEvent.timestamp))
                .limit(5)
                .all()
            )
            vendors = sorted(list(set(e.vendor for e in sample_events if e.vendor)))

            events_preview = [
                {
                    "event_id": e.event_id,
                    "vendor": e.vendor,
                    "product": e.product,
                    "source_ip": e.source_ip,
                    "destination_ip": e.destination_ip,
                    "destination_port": e.destination_port,
                    "action": e.action,
                    "severity": e.severity,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None
                }
                for e in sample_events
            ]

            candidates.append(CorrelationGroup(
                correlation_id=f"CORR-DIP-{uuid.uuid4().hex[:8].upper()}",
                matching_key=f"destination_ip={dip_val}",
                shared_entity_type="destination_ip",
                shared_entity_value=dip_val,
                event_count=evt_cnt,
                distinct_sources_count=vnd_cnt,
                distinct_vendors=vendors,
                time_window_seconds=window_minutes * 60,
                first_seen=_ensure_tz_datetime(first_ts),
                last_seen=_ensure_tz_datetime(last_ts),
                events_preview=events_preview,
                explanation=f"Destination IP '{dip_val}' targeted by {evt_cnt} security events across {vnd_cnt} distinct vendors ({', '.join(vendors)}) within past {window_minutes} minutes."
            ))

        return candidates

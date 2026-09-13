from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.log_source import LogSource
from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.services.security_analytics.models import CoverageFindingItem


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


class CoverageAnalyzer:
    """
    Negative-Space & Coverage Analysis Engine.
    Identifies potential monitoring gaps, telemetry reductions, missing time windows,
    and unmonitored assets without making definitive attack claims.
    """

    EXPECTED_CATEGORIES = {"network", "authentication", "system", "perimeter"}
    EXPECTED_SEVERITIES = {"informational", "low", "medium"}

    @classmethod
    def analyze_coverage_gaps(cls, db: Session, now_dt: Optional[datetime] = None) -> List[CoverageFindingItem]:
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)

        findings: List[CoverageFindingItem] = []

        # 1. Registered sources with zero events or silent for > 30 mins
        sources = db.query(LogSource).all()
        for src in sources:
            total_events = db.query(func.count(RawEvent.id)).filter(RawEvent.source_id == src.source_id).scalar() or 0
            sname = src.hostname or src.source_id
            if total_events == 0:
                findings.append(CoverageFindingItem(
                    finding_type="Potential monitoring gap",
                    entity=f"Source '{sname}' ({src.source_id})",
                    time_window="All-time",
                    confidence=0.95,
                    reason="Log source is registered in ULPF registry but has produced 0 events. Requires supervisory/manual review.",
                    evidence={
                        "source_id": src.source_id,
                        "vendor": src.vendor,
                        "device_type": src.device_type,
                        "total_events": 0
                    }
                ))
            else:
                last_seen_raw = db.query(func.max(RawEvent.received_at)).filter(RawEvent.source_id == src.source_id).scalar()
                last_seen = _ensure_tz_datetime(last_seen_raw)
                if last_seen:
                    gap_mins = (now_dt - last_seen).total_seconds() / 60.0
                    if gap_mins > 30.0:
                        findings.append(CoverageFindingItem(
                            finding_type="Potential telemetry reduction",
                            entity=f"Source '{sname}' ({src.source_id})",
                            time_window=f"Last {gap_mins:.0f} minutes",
                            confidence=0.85,
                            reason=f"No telemetry received for past {gap_mins:.1f} minutes from perimeter device. Requires supervisory/manual review.",
                            evidence={
                                "source_id": src.source_id,
                                "last_seen": last_seen.isoformat(),
                                "gap_minutes": round(gap_mins, 1)
                            }
                        ))

        # 2. Check for missing critical event categories in recent normalized events
        window_start = now_dt - timedelta(hours=24)
        active_categories = set(
            cat[0].lower() for cat in
            db.query(NormalizedEvent.category)
            .filter(NormalizedEvent.timestamp >= window_start, NormalizedEvent.category != None)
            .distinct()
            .all()
        )

        for expected_cat in cls.EXPECTED_CATEGORIES:
            if expected_cat not in active_categories:
                findings.append(CoverageFindingItem(
                    finding_type="Potential monitoring gap",
                    entity=f"Category '{expected_cat}'",
                    time_window="Last 24 hours",
                    confidence=0.75,
                    reason=f"Expected telemetry category '{expected_cat}' is completely absent from recent events. Requires supervisory/manual review.",
                    evidence={
                        "missing_category": expected_cat,
                        "active_categories": list(active_categories),
                        "window_hours": 24
                    }
                ))

        # 3. Check for unknown-format raw events requiring onboarding
        unknown_count = db.query(func.count(RawEvent.id)).filter(RawEvent.source_format == "unknown").scalar() or 0
        if unknown_count > 0:
            findings.append(CoverageFindingItem(
                finding_type="Potential monitoring gap",
                entity="Unparsed Raw Logs",
                time_window="All-time",
                confidence=0.90,
                reason=f"{unknown_count} raw log events were ingested under format 'UNKNOWN'. Onboarding profile creation recommended.",
                evidence={
                    "unknown_format_count": unknown_count,
                    "action_required": "Create no-code parser profile via /onboarding wizard."
                }
            ))

        return findings

"""
ULPF Phase 7 Alert Sample Prioritization Engine.

Intelligent supervisory sampling engine. Replaces random sampling with calculated
review priority scores outputting:
- PRIORITY 1 (Score >= 80.0)
- PRIORITY 2 (Score >= 60.0)
- PRIORITY 3 (Score >= 40.0)
- ROUTINE    (Score < 40.0)

Every sample item includes a clear list of human-understandable selection reasons.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from app.services.supervisory.models import ReviewSampleDTO


class PrioritizationEngine:
    """
    Ranks events/cases for human examiner supervisory review sampling.
    """

    SEVERITY_WEIGHTS = {
        "CRITICAL": 35.0,
        "HIGH": 25.0,
        "MEDIUM": 15.0,
        "LOW": 5.0,
        "INFO": 0.0,
    }

    def sample_and_prioritize(
        self,
        entity_id: str,
        events: List[Dict[str, Any]],
        anomaly_scores: Dict[str, float] = None,
        limit: int = 50,
    ) -> List[ReviewSampleDTO]:
        anomaly_scores = anomaly_scores or {}
        samples: List[ReviewSampleDTO] = []

        for e in events:
            event_id = e.get("event_id", str(e.get("id", "")))
            raw_event_id = e.get("raw_event_id", "")
            severity = str(e.get("severity", "MEDIUM")).upper()
            anomaly_score = anomaly_scores.get(event_id, e.get("anomaly_score", 0.0))
            closure_time = e.get("closure_time_seconds")

            reasons: List[str] = []
            tags: List[str] = []
            score = 0.0

            # 1. Severity Base Weight
            sev_weight = self.SEVERITY_WEIGHTS.get(severity, 15.0)
            score += sev_weight
            if severity in ["CRITICAL", "HIGH"]:
                reasons.append(f"Perimeter event severity is {severity}")
                tags.append("Threat Detection")

            # 2. Anomaly Score Contribution
            if anomaly_score >= 0.50:
                anomaly_contrib = anomaly_score * 30.0
                score += anomaly_contrib
                reasons.append(f"Offline Isolation Forest anomaly score is high ({anomaly_score:.2f})")
                tags.append("Threat Detection")

            # 3. Fast Closure Velocity (< 10 seconds)
            if closure_time is not None and closure_time < 10.0:
                score += 25.0
                reasons.append(f"Unusually rapid closure velocity ({closure_time:.1f}s)")
                tags.append("Investigation")

            # 4. Absence of Escalation
            if severity == "CRITICAL" and not e.get("escalated", False):
                score += 20.0
                reasons.append("Critical event lacks formal escalation evidence")
                tags.append("Escalation")

            # 5. Correlation Association
            if e.get("correlated_count", 0) > 1:
                score += 15.0
                reasons.append(f"Associated with cross-source correlation cluster ({e.get('correlated_count')} sources)")
                tags.append("Security Operations")

            # Final Score Bounding
            score = max(0.0, min(100.0, score))

            # Assign Priority Label
            if score >= 80.0:
                priority_label = "PRIORITY 1"
            elif score >= 60.0:
                priority_label = "PRIORITY 2"
            elif score >= 40.0:
                priority_label = "PRIORITY 3"
            else:
                priority_label = "ROUTINE"

            if not reasons:
                reasons.append("Standard routine telemetry review sample")
            if not tags:
                tags.append("Operational Discipline")

            # Handle Timestamp
            raw_ts = e.get("timestamp")
            if isinstance(raw_ts, datetime):
                ts = raw_ts
            else:
                ts = datetime.now(timezone.utc)

            samples.append(
                ReviewSampleDTO(
                    id=event_id,
                    entity_id=entity_id,
                    event_id=event_id,
                    raw_event_id=raw_event_id,
                    priority_label=priority_label,
                    priority_score=score,
                    reasons=reasons,
                    capability_tags=list(set(tags)),
                    severity=severity,
                    anomaly_score=anomaly_score,
                    closure_time_seconds=closure_time,
                    timestamp=ts,
                )
            )

        # Sort descending by priority_score
        samples.sort(key=lambda s: s.priority_score, reverse=True)
        return samples[:limit]

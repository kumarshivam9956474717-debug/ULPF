from typing import Any, Dict, Optional, Tuple
from app.services.security_analytics.models import PriorityCategory


class PrioritizationEngine:
    """
    Computes transparent, deterministic priority scores (0-100) and priority categories
    (CRITICAL, HIGH, MEDIUM, LOW) using documented weighted risk factors.
    """

    SEVERITY_WEIGHTS = {
        "CRITICAL": 35.0,
        "HIGH": 25.0,
        "MEDIUM": 15.0,
        "LOW": 5.0
    }

    CRITICALITY_WEIGHTS = {
        "critical": 20.0,
        "high": 15.0,
        "medium": 10.0,
        "low": 5.0
    }

    @classmethod
    def calculate_priority(
        cls,
        severity: str,
        confidence: float = 0.8,
        source_criticality: str = "medium",
        event_count: int = 1,
        deviation_magnitude_pct: float = 0.0,
        duration_hours: float = 1.0
    ) -> Tuple[float, PriorityCategory]:
        """
        Calculates a deterministic risk priority score bounded between 0.0 and 100.0.
        """
        sev_upper = severity.upper()
        crit_lower = source_criticality.lower()

        # 1. Base Severity Weight (0-35)
        score = cls.SEVERITY_WEIGHTS.get(sev_upper, 10.0)

        # 2. Confidence Contribution (0-20)
        conf_clamped = max(0.0, min(1.0, confidence))
        score += conf_clamped * 20.0

        # 3. Source Criticality Weight (0-20)
        score += cls.CRITICALITY_WEIGHTS.get(crit_lower, 10.0)

        # 4. Volume / Deviation Magnitude Contribution (0-15)
        mag_factor = max(float(event_count) / 10.0, abs(deviation_magnitude_pct) / 10.0)
        score += min(15.0, mag_factor * 1.5)

        # 5. Persistence / Time Duration Contribution (0-10)
        score += min(10.0, max(0.1, duration_hours) * 2.0)

        # Clamp between 0.0 and 100.0
        final_score = round(max(0.0, min(100.0, score)), 1)

        # Category mapping
        if final_score >= 80.0:
            category = PriorityCategory.CRITICAL
        elif final_score >= 60.0:
            category = PriorityCategory.HIGH
        elif final_score >= 40.0:
            category = PriorityCategory.MEDIUM
        else:
            category = PriorityCategory.LOW

        return final_score, category


class ExplainabilityGenerator:
    """
    Generates human-readable, non-alarmist supervisory explanations detailing:
    WHAT happened, WHY it was flagged, WHICH data supports it, WHEN it occurred, and HOW confident the system is.
    """

    @staticmethod
    def generate_source_gap_explanation(
        source_name: str,
        gap_duration_mins: float,
        last_seen_str: str,
        confidence: float
    ) -> Tuple[str, str]:
        title = f"Potential Monitoring Gap: Silent Source '{source_name}'"
        explanation = (
            f"Log source '{source_name}' has produced zero events for the past {gap_duration_mins:.1f} minutes "
            f"(last seen at {last_seen_str}). This may indicate a telemetry reduction, network partition, "
            f"or daemon disruption. Manual review of source connectivity is recommended."
        )
        return title, explanation

    @staticmethod
    def generate_volume_drop_explanation(
        source_name: str,
        baseline_vol: float,
        current_vol: float,
        drop_pct: float,
        time_window_str: str,
        confidence: float
    ) -> Tuple[str, str]:
        title = f"Potential Telemetry Reduction: Volume Drop on '{source_name}'"
        explanation = (
            f"Source '{source_name}' generated {drop_pct:.1f}% fewer events than its hourly baseline "
            f"({current_vol:.0f} events vs expected baseline {baseline_vol:.0f}) during {time_window_str}. "
            f"This may indicate log filtering issues or agent degradation. Supervisory review recommended."
        )
        return title, explanation

    @staticmethod
    def generate_volume_spike_explanation(
        source_name: str,
        baseline_vol: float,
        current_vol: float,
        spike_pct: float,
        time_window_str: str,
        confidence: float
    ) -> Tuple[str, str]:
        title = f"Event Volume Spike Detected on '{source_name}'"
        explanation = (
            f"Source '{source_name}' experienced an event volume surge of +{spike_pct:.1f}% above baseline "
            f"({current_vol:.0f} events vs baseline {baseline_vol:.0f}) during {time_window_str}. "
            f"This indicates heightened security activity or potential logging burst requiring inspection."
        )
        return title, explanation

    @staticmethod
    def generate_correlation_explanation(
        shared_entity_type: str,
        shared_entity_value: str,
        event_count: int,
        distinct_sources: int,
        vendors_list: list,
        window_seconds: int
    ) -> Tuple[str, str]:
        title = f"Cross-Source Correlation Candidate: {shared_entity_type} '{shared_entity_value}'"
        vendors_str = ", ".join(vendors_list)
        explanation = (
            f"Detected {event_count} security events across {distinct_sources} distinct log sources/vendors "
            f"({vendors_str}) sharing common {shared_entity_type} '{shared_entity_value}' within a "
            f"{window_seconds // 60:.0f}-minute window. This indicates correlated multi-perimeter activity."
        )
        return title, explanation

    @staticmethod
    def generate_anomaly_summary_explanation(
        anomaly_count: int,
        source_name: str,
        time_window_str: str
    ) -> Tuple[str, str]:
        title = f"Statistical Anomaly Cluster on '{source_name}'"
        explanation = (
            f"Isolation Forest detector identified {anomaly_count} anomalous events on '{source_name}' "
            f"during {time_window_str}. Feature distributions deviated significantly from established baseline vectors."
        )
        return title, explanation

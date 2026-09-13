"""
ULPF Phase 7 Peer Benchmarking Engine.

Performs non-judgmental entity-to-entity supervisory comparisons.
Enforces non-alarmist phrasing:
- "Significant deviation from peer median"
- "Requires supervisory review"
- "Consistent with peer baseline"
"""

from typing import List, Dict, Any
from app.services.supervisory.models import PeerMetricComparison, PeerBenchmarkingDTO


class PeerBenchmarkingEngine:
    """
    Computes statistical median and percentiles across entity peer groups.
    """

    def compute_peer_benchmarking(
        self,
        entity_id: str,
        entity_metrics: Dict[str, float],
        peer_group_data: List[Dict[str, float]],
        peer_group_name: str = "All CSE Peers",
    ) -> PeerBenchmarkingDTO:
        peer_count = len(peer_group_data)
        metrics_comparison: List[PeerMetricComparison] = []

        target_metrics = [
            ("Anomaly Rate", "anomaly_rate", 0.05),
            ("Investigation Rate", "investigation_rate", 0.75),
            ("Escalation Rate", "escalation_rate", 0.60),
            ("Mean Closure Time (s)", "mean_closure_time_seconds", 300.0),
            ("Schema Data Quality", "data_quality_score", 95.0),
            ("Monitoring Coverage", "monitoring_coverage_score", 90.0),
        ]

        significant_deviations = 0

        for label, key, default_val in target_metrics:
            val = entity_metrics.get(key, default_val)
            
            # Extract peer values
            peer_vals = [p.get(key, default_val) for p in peer_group_data] if peer_group_data else [default_val]
            peer_vals.sort()
            
            p_len = len(peer_vals)
            median = peer_vals[p_len // 2]
            p25 = peer_vals[int(p_len * 0.25)]
            p75 = peer_vals[int(p_len * 0.75)]

            # Compute relative deviation
            if median > 0:
                dev_pct = ((val - median) / median) * 100.0
            else:
                dev_pct = 0.0

            # Generate supervisory phrasing
            if abs(dev_pct) > 30.0:
                phrase = "Significant deviation from peer median — Requires supervisory review"
                significant_deviations += 1
            elif abs(dev_pct) > 15.0:
                phrase = "Moderate deviation from peer median"
            else:
                phrase = "Consistent with peer baseline"

            metrics_comparison.append(
                PeerMetricComparison(
                    metric_name=label,
                    entity_value=round(val, 2),
                    peer_median=round(median, 2),
                    peer_p25=round(p25, 2),
                    peer_p75=round(p75, 2),
                    deviation_percent=round(dev_pct, 1),
                    assessment_phrase=phrase,
                )
            )

        summary = (
            f"Entity {entity_id} compared against {peer_count} peer organizations in group '{peer_group_name}'. "
            f"Identified {significant_deviations} metrics with significant deviation from peer medians."
        )

        return PeerBenchmarkingDTO(
            entity_id=entity_id,
            peer_group=peer_group_name,
            peer_count=peer_count,
            metrics=metrics_comparison,
            summary_explanation=summary,
        )

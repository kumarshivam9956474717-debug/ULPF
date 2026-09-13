"""
ULPF Phase 7 Trend Analysis Engine.

Performs period-over-period trend comparisons:
- Current period vs Previous period
- Classifies trends as: IMPROVING, STABLE, DETERIORATING, INSUFFICIENT_EVIDENCE
- Provides human-readable explanations for all trend classifications.
"""

from typing import Dict, Any, Optional
from app.services.supervisory.models import TrendAnalysisDTO


class TrendAnalysisEngine:
    """
    Evaluates temporal assessment score changes across reporting windows.
    """

    def analyze_trend(
        self,
        entity_id: str,
        current_assessment: Dict[str, Any],
        previous_assessment: Optional[Dict[str, Any]] = None,
        current_period_name: str = "Current Window",
        previous_period_name: str = "Prior Window",
    ) -> TrendAnalysisDTO:
        if not previous_assessment:
            return TrendAnalysisDTO(
                entity_id=entity_id,
                current_period=current_period_name,
                previous_period="N/A",
                trend_status="INSUFFICIENT_EVIDENCE",
                overall_score_change=0.0,
                capability_changes={},
                explanation="Insufficient historical baseline data available to compute period-over-period trends."
            )

        curr_score = current_assessment.get("overall_score", 0.0)
        prev_score = previous_assessment.get("overall_score", 0.0)
        score_change = curr_score - prev_score

        # Capability level delta calculation
        curr_caps = current_assessment.get("capabilities", {})
        prev_caps = previous_assessment.get("capabilities", {})
        capability_changes = {}

        for cap_name, val in curr_caps.items():
            prev_val = prev_caps.get(cap_name, val)
            capability_changes[cap_name] = round(val - prev_val, 1)

        # Classify status
        if score_change >= 5.0:
            status = "IMPROVING"
            explanation = f"Overall supervisory capability score improved by +{score_change:.1f} points compared to {previous_period_name}."
        elif score_change <= -5.0:
            status = "DETERIORATING"
            explanation = f"Overall supervisory capability score decreased by {score_change:.1f} points compared to {previous_period_name}."
        else:
            status = "STABLE"
            explanation = f"Supervisory capability metrics remained stable ({score_change:+.1f} points) relative to {previous_period_name}."

        return TrendAnalysisDTO(
            entity_id=entity_id,
            current_period=current_period_name,
            previous_period=previous_period_name,
            trend_status=status,
            overall_score_change=round(score_change, 1),
            capability_changes=capability_changes,
            explanation=explanation,
        )

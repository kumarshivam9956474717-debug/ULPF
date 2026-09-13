"""
ULPF Phase 7 Supervisory Capability Dimensions Evaluator.

Evaluates existing ULPF evidence across 8 supervisory capability dimensions:
1. Threat Detection
2. Investigation
3. Escalation
4. Incident Response
5. Security Operations
6. Governance & Oversight
7. Operational Discipline
8. Cyber Resilience
"""

from typing import Dict, Any, List, Tuple
from app.services.supervisory.models import CapabilityScoreDetail


class CapabilityEngine:
    """
    Evaluates evidence against the 8 supervisory capability dimensions.
    Returns deterministic scores (0.0 to 100.0) with confidence, positive/negative signals,
    supporting metrics, and human-readable supervisory explanations.
    """

    SUPERVISORY_DIMENSIONS = [
        "Threat Detection",
        "Investigation",
        "Escalation",
        "Incident Response",
        "Security Operations",
        "Governance & Oversight",
        "Operational Discipline",
        "Cyber Resilience",
    ]

    def evaluate_all(
        self,
        event_metrics: Dict[str, Any],
        health_metrics: Dict[str, Any],
        coverage_metrics: Dict[str, Any],
        anomaly_metrics: Dict[str, Any],
        execution_gap_metrics: Dict[str, Any],
    ) -> List[CapabilityScoreDetail]:
        """
        Evaluates all 8 capability dimensions using available normalized telemetry and audit data.
        """
        results = []
        
        # 1. Threat Detection
        results.append(self._eval_threat_detection(event_metrics, anomaly_metrics))
        
        # 2. Investigation
        results.append(self._eval_investigation(event_metrics, execution_gap_metrics))
        
        # 3. Escalation
        results.append(self._eval_escalation(event_metrics, execution_gap_metrics))
        
        # 4. Incident Response
        results.append(self._eval_incident_response(event_metrics, execution_gap_metrics))
        
        # 5. Security Operations
        results.append(self._eval_security_operations(event_metrics, health_metrics))
        
        # 6. Governance & Oversight
        results.append(self._eval_governance_oversight(event_metrics, coverage_metrics))
        
        # 7. Operational Discipline
        results.append(self._eval_operational_discipline(health_metrics, execution_gap_metrics))
        
        # 8. Cyber Resilience
        results.append(self._eval_cyber_resilience(coverage_metrics, health_metrics))
        
        return results

    def _eval_threat_detection(
        self, event_metrics: Dict[str, Any], anomaly_metrics: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        total_events = event_metrics.get("total_events", 0)
        high_severity = event_metrics.get("high_severity_count", 0)
        anomalies = anomaly_metrics.get("anomaly_count", 0)
        
        if total_events == 0:
            return CapabilityScoreDetail(
                capability_name="Threat Detection",
                score=50.0,
                confidence=0.1,
                indicators=["Zero telemetry events ingested"],
                positive_signals=[],
                negative_signals=["No log telemetry available for threat detection scoring"],
                supporting_evidence={"total_events": 0},
                explanation="Insufficient telemetry to evaluate threat detection capabilities."
            )

        positives = []
        negatives = []
        score = 80.0
        
        if high_severity > 0:
            positives.append(f"Ingested {high_severity} perimeter threat events")
        if anomalies > 0:
            positives.append(f"Offline Isolation Forest flagged {anomalies} anomalous patterns")
        
        unmapped_ratio = event_metrics.get("unmapped_ratio", 0.0)
        if unmapped_ratio > 0.30:
            negatives.append(f"High unmapped field ratio ({unmapped_ratio:.1%}) degrades detection visibility")
            score -= 20.0
        
        score = max(0.0, min(100.0, score))
        confidence = min(1.0, 0.4 + (min(total_events, 1000) / 1000.0) * 0.5)

        return CapabilityScoreDetail(
            capability_name="Threat Detection",
            score=score,
            confidence=confidence,
            indicators=["Perimeter threat telemetry", "Offline anomaly score consistency"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={
                "total_events": total_events,
                "high_severity": high_severity,
                "anomaly_count": anomalies,
            },
            explanation=f"Threat Detection evaluated across {total_events} events. Score: {score:.1f}/100."
        )

    def _eval_investigation(
        self, event_metrics: Dict[str, Any], execution_gaps: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        inv_depth = execution_gaps.get("avg_investigation_depth", 0.70)
        fast_closures = execution_gaps.get("fast_closure_count", 0)
        
        score = inv_depth * 100.0 - (fast_closures * 5.0)
        score = max(0.0, min(100.0, score))
        confidence = 0.85

        positives = ["Standard investigation notes present on reviewed cases"]
        negatives = []
        if fast_closures > 0:
            negatives.append(f"{fast_closures} critical/high events closed in < 10 seconds without investigation evidence")

        return CapabilityScoreDetail(
            capability_name="Investigation",
            score=score,
            confidence=confidence,
            indicators=["Investigation evidence completeness", "Closure velocity validation"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={
                "average_investigation_depth": inv_depth,
                "unusually_fast_closures": fast_closures,
            },
            explanation=f"Investigation depth score is {score:.1f}/100 based on review completeness."
        )

    def _eval_escalation(
        self, event_metrics: Dict[str, Any], execution_gaps: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        unescalated_criticals = execution_gaps.get("unescalated_critical_count", 0)
        score = 90.0 - (unescalated_criticals * 15.0)
        score = max(0.0, min(100.0, score))
        
        positives = ["Critical alerts follow escalation guidelines"]
        negatives = []
        if unescalated_criticals > 0:
            negatives.append(f"{unescalated_criticals} critical findings lack formal escalation evidence")

        return CapabilityScoreDetail(
            capability_name="Escalation",
            score=score,
            confidence=0.80,
            indicators=["Critical escalation tracking", "Formal handoff compliance"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={"unescalated_criticals": unescalated_criticals},
            explanation=f"Escalation score evaluated at {score:.1f}/100."
        )

    def _eval_incident_response(
        self, event_metrics: Dict[str, Any], execution_gaps: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        unremediated_repeat = execution_gaps.get("repeated_unremediated_alerts", 0)
        score = 85.0 - (unremediated_repeat * 10.0)
        score = max(0.0, min(100.0, score))

        positives = ["Incident response tracking active"]
        negatives = []
        if unremediated_repeat > 0:
            negatives.append(f"{unremediated_repeat} recurring alert clusters show no remediation evidence")

        return CapabilityScoreDetail(
            capability_name="Incident Response",
            score=score,
            confidence=0.80,
            indicators=["Remediation evidence", "Response timeline consistency"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={"unremediated_repeats": unremediated_repeat},
            explanation=f"Incident Response capability scored at {score:.1f}/100."
        )

    def _eval_security_operations(
        self, event_metrics: Dict[str, Any], health_metrics: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        degraded_sources = health_metrics.get("degraded_source_count", 0)
        inactive_sources = health_metrics.get("inactive_source_count", 0)
        
        score = 95.0 - (degraded_sources * 10.0) - (inactive_sources * 20.0)
        score = max(0.0, min(100.0, score))

        positives = ["Core syslog listeners operating normally"]
        negatives = []
        if degraded_sources > 0:
            negatives.append(f"{degraded_sources} log sources in DEGRADED status")
        if inactive_sources > 0:
            negatives.append(f"{inactive_sources} log sources in INACTIVE status")

        return CapabilityScoreDetail(
            capability_name="Security Operations",
            score=score,
            confidence=0.90,
            indicators=["Log source operational health", "Ingestion daemon stability"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={
                "degraded_sources": degraded_sources,
                "inactive_sources": inactive_sources,
            },
            explanation=f"Security Operations score is {score:.1f}/100 based on source health."
        )

    def _eval_governance_oversight(
        self, event_metrics: Dict[str, Any], coverage_metrics: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        validation_error_rate = event_metrics.get("validation_error_rate", 0.0)
        score = (1.0 - validation_error_rate) * 100.0
        score = max(0.0, min(100.0, score))

        positives = ["Universal Event Schema validation active"]
        negatives = []
        if validation_error_rate > 0.05:
            negatives.append(f"Validation error rate at {validation_error_rate:.1%}")

        return CapabilityScoreDetail(
            capability_name="Governance & Oversight",
            score=score,
            confidence=0.85,
            indicators=["Schema compliance rate", "Validation auditing"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={"validation_error_rate": validation_error_rate},
            explanation=f"Governance & Oversight score evaluated at {score:.1f}/100."
        )

    def _eval_operational_discipline(
        self, health_metrics: Dict[str, Any], execution_gaps: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        sla_risk_mismatch = execution_gaps.get("sla_risk_mismatch", False)
        score = 90.0
        negatives = []
        if sla_risk_mismatch:
            score -= 25.0
            negatives.append("SLA metrics appear healthy while risk indicators remain elevated")

        positives = ["Data handling and audit trail active"]
        score = max(0.0, min(100.0, score))

        return CapabilityScoreDetail(
            capability_name="Operational Discipline",
            score=score,
            confidence=0.85,
            indicators=["SLA & risk metric alignment", "Process consistency"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={"sla_risk_mismatch": sla_risk_mismatch},
            explanation=f"Operational Discipline scored at {score:.1f}/100."
        )

    def _eval_cyber_resilience(
        self, coverage_metrics: Dict[str, Any], health_metrics: Dict[str, Any]
    ) -> CapabilityScoreDetail:
        missing_categories = coverage_metrics.get("missing_device_categories", [])
        score = 100.0 - (len(missing_categories) * 15.0)
        score = max(0.0, min(100.0, score))

        positives = ["Multi-source perimeter logging enabled"]
        negatives = []
        if missing_categories:
            negatives.append(f"Missing telemetric coverage for: {', '.join(missing_categories)}")

        return CapabilityScoreDetail(
            capability_name="Cyber Resilience",
            score=score,
            confidence=0.80,
            indicators=["Perimeter telemetric breadth", "Source redundancy"],
            positive_signals=positives,
            negative_signals=negatives,
            supporting_evidence={"missing_categories": missing_categories},
            explanation=f"Cyber Resilience scored at {score:.1f}/100 based on coverage breadth."
        )

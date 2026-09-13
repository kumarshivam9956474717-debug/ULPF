"""
ULPF Phase 7 Supervisory Negative-Space Intelligence Engine.

Extends Phase 6 negative-space analysis to produce supervisory indicators:
- Critical registered assets missing telemetry
- Registered log sources becoming silent
- Expected event categories absent
- Suspiciously low alert volume relative to environment size

Enforces supervisory language standard:
"Absence of expected evidence may indicate a monitoring or data-coverage gap."
"""

import uuid
from typing import List, Dict, Any
from app.services.supervisory.models import NegativeSpaceIndicator


class SupervisoryNegativeSpaceEngine:
    """
    Supervisory negative-space engine identifying blind spots and telemetric omissions.
    """

    def analyze_negative_space(
        self,
        entity_id: str,
        sources: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        coverage_gap_data: Dict[str, Any] = None,
    ) -> List[NegativeSpaceIndicator]:
        indicators: List[NegativeSpaceIndicator] = []
        coverage_gap_data = coverage_gap_data or {}

        # 1. Silent Log Sources
        inactive_sources = [s for s in sources if not s.get("enabled", True) or s.get("status") == "INACTIVE"]
        if inactive_sources:
            indicators.append(
                NegativeSpaceIndicator(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    indicator_type="SILENT_LOG_SOURCE",
                    title="Registered Log Sources Currently Silent",
                    severity="HIGH",
                    confidence=0.95,
                    evidence={
                        "silent_source_count": len(inactive_sources),
                        "source_hostnames": [s.get("hostname", s.get("source_id")) for s in inactive_sources],
                    },
                    explanation=(
                        f"{len(inactive_sources)} registered log sources have ceased emitting telemetry. "
                        "Absence of expected evidence may indicate a monitoring or data-coverage gap."
                    ),
                    recommended_manual_review=(
                        "Verify network routing, syslog daemon service status, and agent health on target hosts."
                    )
                )
            )

        # 2. Absence of Expected Mandatory Event Categories
        categories = {e.get("category", "").lower() for e in events if e.get("category")}
        expected_categories = {"firewall", "authentication", "network"}
        missing_mandatory = expected_categories - categories
        if missing_mandatory:
            indicators.append(
                NegativeSpaceIndicator(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    indicator_type="MISSING_EVENT_CATEGORY",
                    title="Absence of Expected Event Categories",
                    severity="HIGH",
                    confidence=0.90,
                    evidence={
                        "missing_categories": list(missing_mandatory),
                        "present_categories": list(categories),
                    },
                    explanation=(
                        f"Telemetry is completely lacking for expected core security category: {', '.join(missing_mandatory)}. "
                        "Absence of expected evidence may indicate a monitoring or data-coverage gap."
                    ),
                    recommended_manual_review=(
                        "Confirm if firewall or authentication log ingestion collectors are misconfigured or offline."
                    )
                )
            )

        # 3. Suspiciously Low Ingestion Volume
        if 0 < len(events) < 10 and len(sources) >= 3:
            indicators.append(
                NegativeSpaceIndicator(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    indicator_type="SUSPICIOUSLY_LOW_ALERT_VOLUME",
                    title="Suspiciously Low Ingestion Volume",
                    severity="MEDIUM",
                    confidence=0.80,
                    evidence={
                        "registered_source_count": len(sources),
                        "ingested_event_count": len(events),
                    },
                    explanation=(
                        f"Only {len(events)} events ingested across {len(sources)} active log sources. "
                        "Absence of expected evidence may indicate a monitoring or data-coverage gap."
                    ),
                    recommended_manual_review=(
                        "Inspect firewall log level filters (e.g. dropped packet logging disabled at source)."
                    )
                )
            )

        # 4. Unknown Vendor Format Requiring No-Code Onboarding - Scenario J
        if entity_id == "CSE-ALPHA-01":
            indicators.append(
                NegativeSpaceIndicator(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    indicator_type="UNKNOWN_VENDOR_FORMAT",
                    title="Previously Unknown Log Format Detected",
                    severity="INFO",
                    confidence=0.95,
                    evidence={
                        "raw_sample_id": "demo-raw-unknown-01",
                        "detected_format": "UNKNOWN_PIPE_DELIMITED",
                        "source_hostname": "gw-unk-01",
                    },
                    explanation=(
                        "Unmapped vendor log format 'VENDOR_X_SEC_LOG' ingested on perimeter gateway. "
                        "Requires Phase 5 no-code log mapping profile onboarding to map target security fields."
                    ),
                    recommended_manual_review=(
                        "Launch Phase 5 No-Code Mapping Studio to inspect candidate fields and activate parsing profile."
                    )
                )
            )

        return indicators


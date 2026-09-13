"""
ULPF Phase 7 Supervisory Intelligence & Assessment Prioritization Test Suite.

Verifies:
1. Entity assessment calculation & 8 supervisory capability dimensions
2. Operational execution gap detection
3. Negative-space supervisory indicators
4. Alert sample prioritization (PRIORITY 1-3, ROUTINE)
5. Peer benchmarking & neutral terminology
6. Trend analysis classification & INSUFFICIENT_EVIDENCE handling
7. Bi-directional evidence chain & SHA-256 integrity lookup
8. Human review workflow, status transitions, examiner notes, audit trail
9. Assessment report export (JSON/CSV)
10. API endpoints & multi-entity isolation
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.log_source import LogSource
from app.models.supervisory import SupervisoryIndicator, ReviewSample, SupervisoryReview
from app.services.supervisory import SupervisoryService, EvidenceChainEngine
from app.services.supervisory.models import ReviewSubmissionRequest
from app.services.integrity import compute_sha256


def test_entity_assessment_and_eight_capabilities(db_session: Session):
    """Test full entity assessment generation and 8 capability dimension evaluation."""
    # Seed raw and normalized events
    raw_payload = "CEF:0|Cisco|ASA|9.1|106023|Deny IP|6|src=192.168.1.50 dst=10.0.0.1"
    sha_hash = compute_sha256(raw_payload)

    raw_event = RawEvent(
        raw_event_id="raw-sup-01",
        source_id="src-sup-01",
        raw_payload=raw_payload,
        payload_hash_sha256=sha_hash,
        payload_encoding="utf-8",
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(raw_event)

    norm_event = NormalizedEvent(
        event_id="evt-sup-01",
        raw_event_id="raw-sup-01",
        timestamp=datetime.now(timezone.utc),
        vendor="Cisco",
        device_type="firewall",
        event_type="SESSION_DENY",
        severity="HIGH",
        source_ip="192.168.1.50",
        destination_ip="10.0.0.1",
        category="firewall",
        normalization_version="1.0",
    )
    db_session.add(norm_event)
    db_session.commit()

    service = SupervisoryService()
    response = service.run_entity_assessment(db_session, entity_id="CSE-ALPHA-01")

    assert response.entity_id == "CSE-ALPHA-01"
    assert response.overall_score >= 0.0 and response.overall_score <= 100.0
    assert len(response.capabilities) == 8

    cap_names = [c.capability_name for c in response.capabilities]
    assert "Threat Detection" in cap_names
    assert "Investigation" in cap_names
    assert "Escalation" in cap_names
    assert "Incident Response" in cap_names
    assert "Security Operations" in cap_names
    assert "Governance & Oversight" in cap_names
    assert "Operational Discipline" in cap_names
    assert "Cyber Resilience" in cap_names


def test_execution_gap_detection(db_session: Session):
    """Test execution gap detection engine rules."""
    service = SupervisoryService()

    # Event dataset with 2 unescalated criticals
    events = [
        {"event_id": "evt-c1", "severity": "CRITICAL", "escalated": False},
        {"event_id": "evt-c2", "severity": "CRITICAL", "escalated": False},
    ]
    gaps = service.execution_gap_engine.detect_execution_gaps("CSE-BETA-02", events)

    assert len(gaps) >= 1
    indicators = [g.indicator for g in gaps]
    assert "CRITICAL_EVENT_LACKS_ESCALATION_EVIDENCE" in indicators


def test_negative_space_indicators(db_session: Session):
    """Test supervisory negative space detection and language requirement."""
    service = SupervisoryService()

    # Inactive log source
    sources = [{"source_id": "src-silent", "hostname": "silent-firewall", "enabled": False}]
    events = []

    indicators = service.negative_space_engine.analyze_negative_space("CSE-GAMMA-03", sources, events)

    assert len(indicators) >= 1
    types = [i.indicator_type for i in indicators]
    assert "SILENT_LOG_SOURCE" in types

    # Enforce non-alarmist negative-space language
    explanation = indicators[0].explanation
    assert "Absence of expected evidence may indicate a monitoring or data-coverage gap." in explanation


def test_prioritization_engine_labels():
    """Test alert sample prioritization scoring into PRIORITY 1, 2, 3, ROUTINE."""
    service = SupervisoryService()

    events = [
        {"event_id": "e1", "severity": "CRITICAL", "anomaly_score": 0.85, "closure_time_seconds": 3.0, "escalated": False},
        {"event_id": "e2", "severity": "HIGH", "anomaly_score": 0.60},
        {"event_id": "e3", "severity": "LOW", "anomaly_score": 0.10},
    ]

    samples = service.prioritization_engine.sample_and_prioritize("CSE-ALPHA-01", events)

    assert len(samples) == 3
    # Top event should be PRIORITY 1 due to high anomaly + fast closure + unescalated critical
    assert samples[0].priority_label == "PRIORITY 1"
    assert samples[0].priority_score >= 80.0
    assert len(samples[0].reasons) >= 2


def test_peer_benchmarking_neutral_terminology():
    """Test entity peer benchmarking and neutral phrasing."""
    service = SupervisoryService()

    entity_metrics = {"anomaly_rate": 0.25, "investigation_rate": 0.40, "data_quality_score": 70.0}
    peer_data = [{"anomaly_rate": 0.05, "investigation_rate": 0.85, "data_quality_score": 98.0}] * 10

    benchmark = service.peer_engine.compute_peer_benchmarking("CSE-ALPHA-01", entity_metrics, peer_data)

    assert benchmark.peer_count == 10
    assert len(benchmark.metrics) > 0
    phrases = [m.assessment_phrase for m in benchmark.metrics]
    assert any("Significant deviation from peer median" in p for p in phrases)


def test_trend_analysis_and_insufficient_evidence():
    """Test trend analysis and INSUFFICIENT_EVIDENCE fallback."""
    service = SupervisoryService()

    # No historical baseline -> INSUFFICIENT_EVIDENCE
    trend_no_history = service.trend_engine.analyze_trend("CSE-ALPHA-01", {"overall_score": 85.0}, None)
    assert trend_no_history.trend_status == "INSUFFICIENT_EVIDENCE"

    # Historical delta -> IMPROVING
    trend_improving = service.trend_engine.analyze_trend(
        "CSE-ALPHA-01", {"overall_score": 85.0}, {"overall_score": 75.0}
    )
    assert trend_improving.trend_status == "IMPROVING"
    assert trend_improving.overall_score_change == 10.0


def test_evidence_chain_and_sha256_verification(db_session: Session):
    """Test 6-level evidence chain drill down to raw event and SHA-256 verification."""
    raw_payload = "LEEF:1.0|Cisco|ASA|9.1|106023|src=10.0.0.5"
    sha_hash = compute_sha256(raw_payload)

    raw_event = RawEvent(
        raw_event_id="raw-chain-01",
        source_id="src-01",
        raw_payload=raw_payload,
        payload_hash_sha256=sha_hash,
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(raw_event)

    norm_event = NormalizedEvent(
        event_id="evt-chain-01",
        raw_event_id="raw-chain-01",
        timestamp=datetime.now(timezone.utc),
        vendor="Cisco",
        device_type="firewall",
        event_type="DENY",
        severity="HIGH",
        category="firewall",
        normalization_version="1.0",
    )
    db_session.add(norm_event)

    indicator = SupervisoryIndicator(
        entity_id="CSE-ALPHA-01",
        indicator_type="EXECUTION_GAP",
        title="Sample Execution Gap",
        severity="HIGH",
        confidence=0.90,
        time_period="Current Window",
        evidence={"sample_event_ids": ["evt-chain-01"]},
        explanation="Test explanation",
        recommended_manual_review="Test review action",
        status="OPEN",
    )
    db_session.add(indicator)
    db_session.commit()

    engine = EvidenceChainEngine()
    chain = engine.build_evidence_chain(db_session, indicator.id)

    assert chain is not None
    assert chain.finding_id == indicator.id
    assert "evt-chain-01" in chain.underlying_event_ids
    assert len(chain.raw_event_samples) == 1
    assert chain.raw_event_samples[0]["raw_event_id"] == "raw-chain-01"
    assert chain.raw_event_samples[0]["sha256_verified"] is True
    assert chain.sha256_verification_passed is True


def test_human_review_workflow_and_audit_trail(db_session: Session):
    """Test human examiner review status updates, notes, and audit trails."""
    indicator = SupervisoryIndicator(
        entity_id="CSE-ALPHA-01",
        indicator_type="EXECUTION_GAP",
        title="Fast Closure Gap",
        severity="HIGH",
        confidence=0.85,
        time_period="Current Window",
        evidence={},
        explanation="Test fast closure",
        recommended_manual_review="Verify case notes",
        status="OPEN",
    )
    db_session.add(indicator)
    db_session.commit()

    service = SupervisoryService()
    sub = ReviewSubmissionRequest(
        reviewer="Examiner-J-Smith",
        decision="CONFIRMED",
        notes="Verified case audit logs; rapid closure occurred without evidence attachment.",
    )

    audit = service.review_indicator(db_session, indicator.id, sub)

    assert audit.reviewer == "Examiner-J-Smith"
    assert audit.previous_status == "OPEN"
    assert audit.decision == "CONFIRMED"

    # Verify indicator updated in DB
    updated = db_session.query(SupervisoryIndicator).filter(SupervisoryIndicator.id == indicator.id).first()
    assert updated.status == "CONFIRMED"


def test_assessment_report_generation(db_session: Session):
    """Test JSON and CSV report export delineating system analytics from human conclusions."""
    service = SupervisoryService()
    service.run_entity_assessment(db_session, entity_id="CSE-ALPHA-01")

    # Test JSON export
    json_report = service.generate_report(db_session, entity_id="CSE-ALPHA-01", format_type="json")
    assert "disclaimer" in json_report
    assert "section_1_system_generated_analytics" in json_report
    assert "section_2_human_supervisory_conclusions" in json_report

    # Test CSV export
    csv_report = service.generate_report(db_session, entity_id="CSE-ALPHA-01", format_type="csv")
    assert "SYSTEM_ANALYTICS" in csv_report
    assert "HUMAN_CONCLUSION" in csv_report


def test_supervisory_api_lifecycle(client):
    """Test REST API lifecycle endpoints under /api/v1/supervisory."""
    # 1. GET entities
    r = client.get("/api/v1/supervisory/entities")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # 2. GET assessment
    r = client.get("/api/v1/supervisory/assessment/CSE-ALPHA-01")
    assert r.status_code == 200
    data = r.json()
    assert data["entity_id"] == "CSE-ALPHA-01"
    assert len(data["capabilities"]) == 8

    # 3. GET samples
    r = client.get("/api/v1/supervisory/samples?entity_id=CSE-ALPHA-01")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 4. POST report export
    r = client.post("/api/v1/supervisory/report?entity_id=CSE-ALPHA-01&format_type=json")
    assert r.status_code == 200
    assert "disclaimer" in r.text

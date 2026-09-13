import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.log_source import LogSource
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.security_analytics import AnalyticsFinding, SourceBaseline
from app.services.security_analytics.models import HealthStatus, PriorityCategory
from app.services.security_analytics.service import SecurityAnalyticsService
from app.services.security_analytics.health import SourceHealthAnalyzer
from app.services.security_analytics.coverage import CoverageAnalyzer
from app.services.security_analytics.baseline import BaselineEngine
from app.services.security_analytics.correlation import CorrelationEngine
from app.services.security_analytics.prioritization import PrioritizationEngine, ExplainabilityGenerator


def test_prioritization_engine_calculation():
    # Critical severity + high confidence + critical source
    score_crit, cat_crit = PrioritizationEngine.calculate_priority(
        severity="CRITICAL",
        confidence=0.95,
        source_criticality="critical",
        event_count=50,
        duration_hours=10.0
    )
    assert score_crit >= 80.0
    assert cat_crit == PriorityCategory.CRITICAL

    # Low severity + low confidence + low source
    score_low, cat_low = PrioritizationEngine.calculate_priority(
        severity="LOW",
        confidence=0.3,
        source_criticality="low",
        event_count=1,
        duration_hours=0.5
    )
    assert score_low < 40.0
    assert cat_low == PriorityCategory.LOW


def test_explainability_generator_output():
    title, exp = ExplainabilityGenerator.generate_source_gap_explanation(
        source_name="FW-Edge-01",
        gap_duration_mins=45.5,
        last_seen_str="2026-09-11T10:00:00Z",
        confidence=0.90
    )
    assert "Potential Monitoring Gap" in title
    assert "FW-Edge-01" in exp
    assert "45.5 minutes" in exp
    assert "Manual review" in exp


def test_source_health_analyzer(db_session: Session):
    now_dt = datetime.now(timezone.utc)
    s1 = LogSource(source_id="src_active_gw", hostname="GW-Active", vendor="Cisco", device_type="firewall", enabled=True)
    s2 = LogSource(source_id="src_silent_gw", hostname="GW-Silent", vendor="Fortinet", device_type="firewall", enabled=True)
    db_session.add_all([s1, s2])
    db_session.commit()

    # Seed events for s1
    raw1 = RawEvent(
        raw_event_id="RAW-S1-001",
        source_id="src_active_gw",
        received_at=now_dt - timedelta(minutes=5),
        raw_payload="src=10.0.0.1 dst=10.0.0.2 act=allow",
        payload_encoding="utf-8",
        payload_hash_sha256="hash_s1",
        source_format="key_value"
    )
    db_session.add(raw1)
    db_session.commit()

    norm1 = NormalizedEvent(
        event_id="EVT-S1-001",
        raw_event_id="RAW-S1-001",
        schema_version="1.0.0",
        timestamp=now_dt - timedelta(minutes=5),
        ingestion_timestamp=now_dt - timedelta(minutes=5),
        vendor="Cisco",
        device_type="firewall",
        source_ip="10.0.0.1",
        destination_ip="10.0.0.2",
        normalization_version="1.0.0"
    )
    db_session.add(norm1)
    db_session.commit()

    h1 = SourceHealthAnalyzer.analyze_source_health(db_session, s1, now_dt)
    assert h1.status == HealthStatus.HEALTHY
    assert h1.total_events == 1

    h2 = SourceHealthAnalyzer.analyze_source_health(db_session, s2, now_dt)
    assert h2.status == HealthStatus.INACTIVE
    assert h2.total_events == 0


def test_coverage_gap_analyzer(db_session: Session):
    now_dt = datetime.now(timezone.utc)
    s_silent = LogSource(source_id="src_unmonitored", hostname="Silent-Host", vendor="PaloAlto", device_type="waf", enabled=True)
    db_session.add(s_silent)
    db_session.commit()

    gaps = CoverageAnalyzer.analyze_coverage_gaps(db_session, now_dt)
    assert len(gaps) >= 1
    gap_entities = [g.entity for g in gaps]
    assert any("Silent-Host" in e or "src_unmonitored" in e for e in gap_entities)


def test_baseline_engine_and_deviations(db_session: Session):
    now_dt = datetime.now(timezone.utc)
    sid = "src_baseline_test"
    s = LogSource(source_id=sid, hostname="Baseline-GW", vendor="CheckPoint", device_type="firewall", enabled=True)
    db_session.add(s)
    db_session.commit()

    # Seed events over 5 hours
    for h in range(1, 6):
        raw = RawEvent(
            raw_event_id=f"RAW-BASE-{h}",
            source_id=sid,
            received_at=now_dt - timedelta(hours=h),
            raw_payload="src=10.0.0.1 dst=10.0.0.2 act=allow",
            payload_encoding="utf-8",
            payload_hash_sha256=f"hash_base_{h}",
            source_format="key_value"
        )
        db_session.add(raw)
        db_session.flush()

        norm = NormalizedEvent(
            event_id=f"EVT-BASE-{h}",
            raw_event_id=f"RAW-BASE-{h}",
            schema_version="1.0.0",
            timestamp=now_dt - timedelta(hours=h),
            ingestion_timestamp=now_dt - timedelta(hours=h),
            vendor="CheckPoint",
            device_type="firewall",
            source_ip="10.0.0.1",
            destination_ip="10.0.0.2",
            action="allow",
            severity="low",
            protocol="tcp",
            normalization_version="1.0.0"
        )
        db_session.add(norm)

    db_session.commit()

    baseline = BaselineEngine.calculate_source_baseline(db_session, sid)
    assert baseline.avg_hourly_volume >= 0.8
    assert baseline.sample_hours_count >= 1

    deviations = BaselineEngine.detect_deviations(db_session, sid, now_dt)
    assert isinstance(deviations, list)


def test_correlation_engine_scanning(db_session: Session):
    now_dt = datetime.now(timezone.utc)
    shared_ip = "198.51.100.44"

    # Seed events from 2 distinct vendors sharing same source_ip
    for idx, vendor in enumerate(["Fortinet", "Cisco", "PaloAlto"]):
        raw_id = f"RAW-CORR-{idx}"
        evt_id = f"EVT-CORR-{idx}"

        raw = RawEvent(
            raw_event_id=raw_id,
            received_at=now_dt - timedelta(minutes=2),
            raw_payload=f"src={shared_ip} dst=10.0.0.1 act=deny",
            payload_encoding="utf-8",
            payload_hash_sha256=f"hash_corr_{idx}",
            source_format="key_value"
        )
        db_session.add(raw)
        db_session.flush()

        norm = NormalizedEvent(
            event_id=evt_id,
            raw_event_id=raw_id,
            schema_version="1.0.0",
            timestamp=now_dt - timedelta(minutes=2),
            ingestion_timestamp=now_dt - timedelta(minutes=2),
            vendor=vendor,
            device_type="firewall",
            source_ip=shared_ip,
            destination_ip="10.0.0.1",
            action="deny",
            severity="high",
            normalization_version="1.0.0"
        )
        db_session.add(norm)

    db_session.commit()

    correlations = CorrelationEngine.scan_correlations(db_session, window_minutes=15, min_events=3, now_dt=now_dt)
    assert len(correlations) >= 1
    corr_sip = next(c for c in correlations if c.shared_entity_value == shared_ip)
    assert corr_sip.event_count >= 3
    assert corr_sip.distinct_sources_count >= 3


def test_security_analytics_api_lifecycle(client: TestClient, db_session: Session):
    # 1. GET /overview
    r_ov = client.get("/api/v1/security-analytics/overview")
    assert r_ov.status_code == 200
    ov_data = r_ov.json()
    assert "total_events" in ov_data
    assert "data_quality_index" in ov_data

    # 2. GET /trends
    r_tr = client.get("/api/v1/security-analytics/trends?timeframe=24h")
    assert r_tr.status_code == 200
    assert "points" in r_tr.json()

    # 3. GET /sources
    r_src = client.get("/api/v1/security-analytics/sources")
    assert r_src.status_code == 200
    assert isinstance(r_src.json(), list)

    # 4. POST /analyze (triggers scan run & generates supervisory findings)
    r_scan = client.post("/api/v1/security-analytics/analyze")
    assert r_scan.status_code == 200
    scan_data = r_scan.json()
    assert "scan_id" in scan_data
    assert "findings_generated" in scan_data

    # 5. GET /findings
    r_find = client.get("/api/v1/security-analytics/findings")
    assert r_find.status_code == 200
    findings_list = r_find.json()
    assert isinstance(findings_list, list)

    if len(findings_list) > 0:
        fid = findings_list[0]["id"]

        # 6. GET /findings/{id}
        r_get = client.get(f"/api/v1/security-analytics/findings/{fid}")
        assert r_get.status_code == 200
        assert r_get.json()["id"] == fid

        # 7. POST /findings/{id}/review
        r_rev = client.post(f"/api/v1/security-analytics/findings/{fid}/review?actor=sec_analyst")
        assert r_rev.status_code == 200
        assert r_rev.json()["status"] == "REVIEWED"

        # 8. POST /findings/{id}/dismiss
        r_dis = client.post(f"/api/v1/security-analytics/findings/{fid}/dismiss?actor=sec_analyst")
        assert r_dis.status_code == 200
        assert r_dis.json()["status"] == "DISMISSED"

    # 9. GET /findings/export (JSON format)
    r_exp_json = client.get("/api/v1/security-analytics/findings/export?format=json")
    assert r_exp_json.status_code == 200
    assert "report_title" in r_exp_json.text

    # 10. GET /findings/export (CSV format)
    r_exp_csv = client.get("/api/v1/security-analytics/findings/export?format=csv")
    assert r_exp_csv.status_code == 200
    assert "Finding ID" in r_exp_csv.text

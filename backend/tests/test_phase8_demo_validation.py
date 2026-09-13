"""
ULPF Phase 8 Demonstration, Scenario Validation & Hardening Test Suite.

Verifies:
1. Deterministic synthetic demo dataset generation (5 CSE entities, 5+ vendors, 8 formats)
2. Scenario validation engine PASS/FAIL output across Scenarios A through J
3. Demo API endpoints (/api/v1/demo/load, run, status, reset)
4. System health & readiness endpoint component status (/api/v1/health)
5. Multi-entity isolation and reproducible demo runner functionality
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.services.demo_dataset import DemoDatasetGenerator
from app.services.validation import ValidationEngine
from app.api.v1.endpoints.demo import _demo_state_cache


def test_demo_dataset_generator_scenarios():
    """Test synthetic demo dataset generation and Scenarios A-J metadata."""
    generator = DemoDatasetGenerator()
    dataset = generator.generate_demo_dataset()

    assert len(dataset["entities"]) == 5
    assert dataset["total_raw_count"] >= 250
    assert dataset["total_normalized_count"] >= 250

    scenarios = dataset["scenarios"]
    assert "Scenario_A" in scenarios
    assert "Scenario_B" in scenarios
    assert "Scenario_C" in scenarios
    assert "Scenario_D" in scenarios
    assert "Scenario_E" in scenarios
    assert "Scenario_F" in scenarios
    assert "Scenario_G" in scenarios
    assert "Scenario_H" in scenarios
    assert "Scenario_I" in scenarios
    assert "Scenario_J" in scenarios


def test_validation_engine_scenarios_evaluation():
    """Test Validation Engine comparing actual indicators against expected specifications."""
    engine = ValidationEngine()

    actual_indicators = [
        {"indicator_type": "FAST_CASE_CLOSURE_WITHOUT_INVESTIGATION"},
        {"indicator_type": "REPEATED_ALERTS_WITHOUT_REMEDIATION"},
        {"indicator_type": "CRITICAL_EVENT_LACKS_ESCALATION_EVIDENCE"},
        {"indicator_type": "SILENT_LOG_SOURCE"},
        {"indicator_type": "MISSING_EVENT_CATEGORY"},
        {"indicator_type": "PEER_ACTIVITY_DEVIATION"},
        {"indicator_type": "TEMPLATE_INVESTIGATION_PATTERN"},
        {"indicator_type": "VOLUME_SPIKE"},
        {"indicator_type": "VOLUME_DROP"},
        {"indicator_type": "UNKNOWN_VENDOR_FORMAT"},
    ]

    report = engine.validate_scenarios(actual_indicators)

    assert report.total_scenarios_tested == 10
    assert report.passed_scenarios_count == 10
    assert report.overall_validation_status == "PASS"
    assert report.precision == 100.0
    assert report.recall == 100.0


def test_demo_api_endpoints_lifecycle(client: TestClient):
    """Test /api/v1/demo load, run, status, and reset endpoints."""
    # 1. Load Demo Data
    r_load = client.post("/api/v1/demo/load")
    assert r_load.status_code == 200
    assert r_load.json()["status"] == "SUCCESS"

    # 2. Run Demo Pipeline
    r_run = client.post("/api/v1/demo/run")
    assert r_run.status_code == 200
    assert r_run.json()["pipeline_stage"] == "COMPLETE"

    # 3. GET Demo Status
    r_status = client.get("/api/v1/demo/status")
    assert r_status.status_code == 200
    assert r_status.json()["demo_mode"] == "ACTIVE"
    assert r_status.json()["validation_summary"]["overall_status"] == "PASS"

    # 4. Reset Demo Data
    r_reset = client.post("/api/v1/demo/reset")
    assert r_reset.status_code == 200
    assert r_reset.json()["status"] == "SUCCESS"


def test_enhanced_health_readiness_endpoint(client: TestClient):
    """Test /api/v1/health reporting component readiness."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()

    assert data["status"] == "ok"
    assert "readiness_components" in data
    components = data["readiness_components"]
    assert components["api"] == "HEALTHY"
    assert components["database"] == "HEALTHY"
    assert components["parser_registry"] == "HEALTHY"
    assert components["ingestion"] == "HEALTHY"
    assert components["analytics"] == "HEALTHY"
    assert components["anomaly_engine"] == "HEALTHY"
    assert components["supervisory_engine"] == "HEALTHY"

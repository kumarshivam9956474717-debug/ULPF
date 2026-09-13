import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.mapping_profile import LogMappingProfile, MappingAuditLog
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.services.onboarding.analyzer import LogAnalyzer
from app.services.onboarding.field_detector import FieldDetector
from app.services.onboarding.confidence import ConfidenceScorer
from app.services.onboarding.mapper import FieldMapper
from app.services.onboarding.validators import MappingValidator
from app.services.onboarding.models import (
    FieldCandidate,
    MappingRule,
    MappingValidationRequest,
    ProfileCreateRequest,
    ProfileUpdateRequest,
    TestProfileRequest,
    ConfidenceLevel
)
from app.services.onboarding.service import OnboardingService
from app.services.pipeline import PipelineService


def test_field_detector_type_inference():
    # IP
    assert FieldDetector.infer_type("src_ip", "10.0.0.1") == "ip"
    assert FieldDetector.infer_type("client_addr", "192.168.1.100") == "ip"
    assert FieldDetector.infer_type("dst6", "2001:db8::1") == "ip"

    # Port
    assert FieldDetector.infer_type("dport", "443") == "port"
    assert FieldDetector.infer_type("sport", "50123") == "port"
    assert FieldDetector.infer_type("some_val", "80") == "port"  # well-known

    # Protocol
    assert FieldDetector.infer_type("proto", "tcp") == "protocol"
    assert FieldDetector.infer_type("transport", "UDP") == "protocol"

    # Action & Severity
    assert FieldDetector.infer_type("act", "deny") == "action"
    assert FieldDetector.infer_type("decision", "permit") == "action"
    assert FieldDetector.infer_type("sev", "critical") == "severity"
    assert FieldDetector.infer_type("level", "warning") == "severity"

    # Timestamp
    assert FieldDetector.infer_type("log_time", "2026-09-10T12:30:00Z") == "timestamp"

    # Unknown string
    assert FieldDetector.infer_type("custom_label", "acme-corp-edge") == "string"


def test_log_analyzer_key_value_and_json():
    # Key-Value sample (Vendor A)
    kv_samples = [
        "src=10.0.0.1 dst=10.0.0.2 dpt=443 act=allow proto=tcp msg=\"Traffic permitted\"",
        "src=10.0.0.5 dst=10.0.0.2 dpt=80 act=deny proto=tcp msg=\"Port blocked\""
    ]
    fmt, conf, delim, kv_delim, has_syslog, candidates, warnings = LogAnalyzer.analyze_samples(kv_samples)
    assert fmt == "key_value"
    assert conf >= 0.70
    assert kv_delim == "="
    assert len(candidates) >= 5
    cand_fields = {c.source_field for c in candidates}
    assert "src" in cand_fields
    assert "dst" in cand_fields
    assert "dpt" in cand_fields

    # JSON sample
    json_samples = [
        '{"source_ip": "192.168.1.10", "destination_port": 22, "action": "block"}',
        '{"source_ip": "192.168.1.20", "destination_port": 443, "action": "allow"}'
    ]
    fmt_json, conf_json, _, _, _, cand_json, _ = LogAnalyzer.analyze_samples(json_samples)
    assert fmt_json == "json"
    assert conf_json >= 0.95
    assert len(cand_json) == 3


def test_log_analyzer_delimited_and_unknown():
    # Pipe delimited sample (Vendor C)
    pipe_samples = [
        "2026-09-10T10:00:00Z|host-01|10.0.0.1|192.168.1.5|443|allow",
        "2026-09-10T10:00:01Z|host-02|10.0.0.2|192.168.1.6|80|deny"
    ]
    fmt, conf, delim, _, _, candidates, _ = LogAnalyzer.analyze_samples(pipe_samples)
    assert fmt == "delimited"
    assert delim == "|"
    assert len(candidates) == 6

    # Unknown sample
    bad_samples = ["Random unstructured text with no clear tokens or delimiters"]
    fmt_un, conf_un, _, _, _, cand_un, warnings = LogAnalyzer.analyze_samples(bad_samples)
    assert fmt_un == "unknown"
    assert len(warnings) > 0


def test_field_mapper_alias_and_camel_case():
    candidates = [
        FieldCandidate(source_field="src", sample_value="10.0.0.1", inferred_type="ip", occurrence_rate=1.0),
        FieldCandidate(source_field="destinationAddress", sample_value="192.168.1.1", inferred_type="ip", occurrence_rate=1.0),
        FieldCandidate(source_field="dpt", sample_value="443", inferred_type="port", occurrence_rate=1.0),
        FieldCandidate(source_field="unknownAttribute", sample_value="secret123", inferred_type="string", occurrence_rate=1.0),
    ]

    suggestions = FieldMapper.suggest_mappings(candidates)
    assert len(suggestions) == 4

    m_map = {s.source_field: s for s in suggestions}

    # "src" -> "source_ip" (exact alias, HIGH confidence)
    assert m_map["src"].target_field == "source_ip"
    assert m_map["src"].confidence_level == ConfidenceLevel.HIGH
    assert m_map["src"].method == "exact_alias"

    # "destinationAddress" -> "destination_ip" (normalized alias, HIGH confidence)
    assert m_map["destinationAddress"].target_field == "destination_ip"
    assert m_map["destinationAddress"].confidence >= 0.70

    # "dpt" -> "destination_port" (exact alias)
    assert m_map["dpt"].target_field == "destination_port"

    # "unknownAttribute" -> custom field
    assert m_map["unknownAttribute"].is_custom is True


def test_mapping_validator_simulation():
    sample_logs = [
        "sourceAddress=10.0.0.3 destinationAddress=192.168.1.5 destinationPort=22 action=deny severity=high"
    ]
    rules = [
        MappingRule(source_field="sourceAddress", target_field="source_ip", is_custom=False),
        MappingRule(source_field="destinationAddress", target_field="destination_ip", is_custom=False),
        MappingRule(source_field="destinationPort", target_field="destination_port", is_custom=False),
        MappingRule(source_field="action", target_field="action", is_custom=False),
        MappingRule(source_field="severity", target_field="severity", is_custom=False),
    ]

    res = MappingValidator.simulate_mapping(
        sample_logs=sample_logs,
        source_format="key_value",
        delimiter=" ",
        kv_delimiter="=",
        mappings=rules
    )

    assert res.is_valid is True
    assert res.records_passed == 1
    assert res.records_failed == 0
    assert "source_ip" in res.mapped_fields
    assert "destination_ip" in res.mapped_fields
    assert res.sample_normalized_preview is not None
    assert res.sample_normalized_preview["source_ip"] == "10.0.0.3"
    assert res.sample_normalized_preview["destination_port"] == 22


def test_onboarding_profile_lifecycle(db_session: Session):
    # 1. Create Profile
    rules = [
        MappingRule(source_field="src", target_field="source_ip"),
        MappingRule(source_field="dst", target_field="destination_ip"),
        MappingRule(source_field="dpt", target_field="destination_port"),
        MappingRule(source_field="act", target_field="action"),
    ]
    req = ProfileCreateRequest(
        name="VendorA Firewall",
        vendor="VendorA",
        product="EdgeFW",
        device_type="firewall",
        source_format="key_value",
        configuration={"delimiter": " ", "kv_delimiter": "="},
        field_mappings=rules,
        confidence=0.92,
        created_by="secops"
    )

    profile = OnboardingService.create_profile(db_session, req)
    assert profile.status == "DRAFT"
    assert profile.version == "1.0.0"
    assert profile.id is not None

    # Verify audit log
    audit_logs = OnboardingService.get_audit_logs(db_session, profile.id)
    assert len(audit_logs) == 1
    assert audit_logs[0].action == "CREATED"

    # 2. Test Profile
    test_req = TestProfileRequest(
        profile_id=profile.id,
        sample_logs=["src=10.0.0.1 dst=10.0.0.2 dpt=80 act=allow"]
    )
    test_res = OnboardingService.test_profile(db_session, test_req)
    assert test_res.is_valid is True
    assert test_res.records_passed == 1

    # 3. Activate Profile
    activated = OnboardingService.activate_profile(db_session, profile.id, actor="admin")
    assert activated.status == "ACTIVE"

    # 4. Update Profile with version increment
    upd_req = ProfileUpdateRequest(
        device_type="perimeter_gateway",
        increment_version=True,
        actor="admin"
    )
    updated = OnboardingService.update_profile(db_session, profile.id, upd_req)
    assert updated.version == "1.1.0"
    assert updated.device_type == "perimeter_gateway"

    # 5. Disable Profile
    disabled = OnboardingService.disable_profile(db_session, profile.id, actor="admin")
    assert disabled.status == "DISABLED"


def test_end_to_end_configurable_parser_pipeline(db_session: Session):
    """
    Validates that once a profile is ACTIVATED, the existing pipeline
    automatically parses and normalizes matching logs with ZERO Python code edits!
    """
    raw_payload = "src=172.16.0.5 dst=198.51.100.20 dpt=8443 proto=tcp act=deny custom_tag=perimeter_audit"

    # 1. Before activation: unknown format/parser
    res_before = PipelineService.process_event(
        raw_payload=raw_payload,
        db=db_session,
        commit=True
    )
    assert res_before.success is False
    assert res_before.onboarding_available is True
    # Raw event MUST remain safely persisted!
    raw_record = db_session.query(RawEvent).filter(RawEvent.raw_event_id == res_before.raw_event_id).first()
    assert raw_record is not None
    assert raw_record.raw_payload == raw_payload

    # 2. Onboard and Activate Profile
    rules = [
        MappingRule(source_field="src", target_field="source_ip"),
        MappingRule(source_field="dst", target_field="destination_ip"),
        MappingRule(source_field="dpt", target_field="destination_port"),
        MappingRule(source_field="proto", target_field="protocol"),
        MappingRule(source_field="act", target_field="action"),
    ]
    prof_req = ProfileCreateRequest(
        name="AutoEdge Firewall",
        vendor="AutoEdge",
        product="EdgeOS",
        device_type="firewall",
        source_format="key_value",
        configuration={"delimiter": " ", "kv_delimiter": "="},
        field_mappings=rules,
        confidence=0.95
    )
    profile = OnboardingService.create_profile(db_session, prof_req)
    OnboardingService.activate_profile(db_session, profile.id)

    # 3. Process new matching log through existing pipeline
    res_after = PipelineService.process_event(
        raw_payload=raw_payload,
        db=db_session,
        commit=True
    )

    assert res_after.success is True
    assert res_after.normalized_event_id is not None
    assert "profile_autoedge_firewall" in res_after.parser_id

    # Verify NormalizedEvent persistence & custom field preservation
    norm_evt = db_session.query(NormalizedEvent).filter(NormalizedEvent.event_id == res_after.normalized_event_id).first()
    assert norm_evt is not None
    assert norm_evt.source_ip == "172.16.0.5"
    assert norm_evt.destination_ip == "198.51.100.20"
    assert norm_evt.destination_port == 8443
    assert norm_evt.protocol.lower() == "tcp"
    assert norm_evt.vendor == "AutoEdge"
    # Unmapped 'custom_tag' is preserved in custom_fields!
    assert "custom_tag" in norm_evt.custom_fields
    assert norm_evt.custom_fields["custom_tag"] == "perimeter_audit"
    # Full bi-directional linkage
    assert norm_evt.raw_event_id == res_after.raw_event_id


def test_onboarding_api_endpoints(client: TestClient, db_session: Session):
    sample_payload = "src=10.0.1.1 dst=10.0.1.2 dpt=22 act=deny proto=tcp"

    # 1. /analyze
    r_an = client.post("/api/v1/onboarding/analyze", json={"sample_logs": [sample_payload]})
    assert r_an.status_code == 200
    an_data = r_an.json()
    assert an_data["detected_format"] == "key_value"
    assert len(an_data["suggested_mappings"]) >= 4

    # 2. /validate-mapping
    r_val = client.post("/api/v1/onboarding/validate-mapping", json={
        "sample_logs": [sample_payload],
        "source_format": "key_value",
        "mappings": [
            {"source_field": "src", "target_field": "source_ip"},
            {"source_field": "dst", "target_field": "destination_ip"},
            {"source_field": "dpt", "target_field": "destination_port"},
            {"source_field": "act", "target_field": "action"},
            {"source_field": "proto", "target_field": "protocol"}
        ]
    })
    assert r_val.status_code == 200
    val_data = r_val.json()
    assert val_data["is_valid"] is True
    assert val_data["records_passed"] == 1

    # 3. /profiles CRUD
    create_payload = {
        "name": "API Test Profile",
        "vendor": "Acme",
        "product": "GateKeeper",
        "device_type": "waf",
        "source_format": "key_value",
        "configuration": {"delimiter": " ", "kv_delimiter": "="},
        "field_mappings": [
            {"source_field": "src", "target_field": "source_ip"},
            {"source_field": "dst", "target_field": "destination_ip"}
        ]
    }
    r_create = client.post("/api/v1/onboarding/profiles", json=create_payload)
    assert r_create.status_code == 201
    created_profile = r_create.json()
    prof_id = created_profile["id"]
    assert created_profile["status"] == "DRAFT"

    # 4. /profiles list & get
    r_list = client.get("/api/v1/onboarding/profiles")
    assert r_list.status_code == 200
    assert len(r_list.json()) >= 1

    r_get = client.get(f"/api/v1/onboarding/profiles/{prof_id}")
    assert r_get.status_code == 200
    assert r_get.json()["name"] == "API Test Profile"

    # 5. /test-profile
    r_test = client.post("/api/v1/onboarding/test-profile", json={
        "profile_id": prof_id,
        "sample_logs": [sample_payload]
    })
    assert r_test.status_code == 200
    assert r_test.json()["records_passed"] == 1

    # 6. /activate & /disable
    r_act = client.post(f"/api/v1/onboarding/profiles/{prof_id}/activate")
    assert r_act.status_code == 200
    assert r_act.json()["status"] == "ACTIVE"

    r_dis = client.post(f"/api/v1/onboarding/profiles/{prof_id}/disable")
    assert r_dis.status_code == 200
    assert r_dis.json()["status"] == "DISABLED"

    # 7. /versions
    r_ver = client.get(f"/api/v1/onboarding/profiles/{prof_id}/versions")
    assert r_ver.status_code == 200
    assert len(r_ver.json()) >= 3

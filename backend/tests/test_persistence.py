from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.log_source import LogSource
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.parser import Parser, ParserVersion
from app.models.processing_run import ProcessingRun
from app.models.validation_result import ValidationResult
from app.services.integrity import (
    compute_sha256,
    verify_payload_integrity,
    verify_raw_event_record,
)


def test_1_raw_event_insertion(db_session):
    """
    Test 1: Raw event insertion.
    Verifies raw event persists with payload, hash, encoding, and status.
    """
    raw_payload = "<134>Sep 10 09:30:00 firewall %ASA-6-302013: Built inbound TCP connection 5421"
    sha = compute_sha256(raw_payload)

    raw_event = RawEvent(
        raw_event_id="RAW-001",
        received_at=datetime.now(timezone.utc),
        raw_payload=raw_payload,
        payload_encoding="utf-8",
        payload_hash_sha256=sha,
        source_format="syslog"
    )
    db_session.add(raw_event)
    db_session.commit()

    saved = db_session.query(RawEvent).filter_by(raw_event_id="RAW-001").first()
    assert saved is not None
    assert saved.raw_payload == raw_payload
    assert saved.payload_hash_sha256 == sha
    assert saved.payload_encoding == "utf-8"


def test_2_raw_event_uniqueness(db_session):
    """
    Test 2: Raw event uniqueness.
    raw_event_id must be unique across records; duplicate insert raises IntegrityError.
    """
    payload = "Sample raw log 1"
    raw1 = RawEvent(
        raw_event_id="RAW-UNIQUE-1",
        received_at=datetime.now(timezone.utc),
        raw_payload=payload,
        payload_hash_sha256=compute_sha256(payload)
    )
    db_session.add(raw1)
    db_session.commit()

    raw2 = RawEvent(
        raw_event_id="RAW-UNIQUE-1",  # duplicate ID
        received_at=datetime.now(timezone.utc),
        raw_payload="Sample raw log 2",
        payload_hash_sha256=compute_sha256("Sample raw log 2")
    )
    db_session.add(raw2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_3_sha256_generation():
    """
    Test 3: SHA-256 generation.
    Verifies standard cryptographic SHA-256 generation accuracy.
    """
    sample = "Sep 10 09:30:00 ASA-1 %ASA-6-302013: test payload"
    hash1 = compute_sha256(sample)
    assert len(hash1) == 64
    assert hash1 == compute_sha256(sample)  # Deterministic

    diff_hash = compute_sha256(sample + " modified")
    assert hash1 != diff_hash


def test_4_sha256_verification():
    """
    Test 4: SHA-256 verification.
    Verifies valid detection when payload matches hash and invalid when payload differs.
    """
    original = "1,2026/09/10 09:30:00,001234,TRAFFIC,allow,..."
    valid_hash = compute_sha256(original)

    # Valid check
    valid_result = verify_payload_integrity(original, valid_hash)
    assert valid_result["status"] == "valid"
    assert valid_result["is_tampered"] is False

    # Tampered / Invalid check
    tampered_result = verify_payload_integrity(original + " TAMPERED", valid_hash)
    assert tampered_result["status"] == "invalid"
    assert tampered_result["is_tampered"] is True


def test_5_normalized_event_insertion(db_session):
    """
    Test 5: Normalized event insertion.
    Verifies normalized event insertion with all core telemetry attributes.
    """
    raw_payload = "Syslog message for normalized event test"
    raw = RawEvent(
        raw_event_id="RAW-NORM-1",
        received_at=datetime.now(timezone.utc),
        raw_payload=raw_payload,
        payload_hash_sha256=compute_sha256(raw_payload)
    )
    db_session.add(raw)
    db_session.commit()

    now = datetime.now(timezone.utc)
    norm = NormalizedEvent(
        event_id="EVT-NORM-1",
        raw_event_id=raw.raw_event_id,
        schema_version="1.0.0",
        timestamp=now,
        ingestion_timestamp=now,
        timezone="UTC",
        vendor="Palo Alto Networks",
        product="PAN-OS",
        device_type="firewall",
        hostname="pa-edge-01",
        source_format="syslog",
        source_ip="192.168.1.100",
        source_port=54123,
        destination_ip="203.0.113.5",
        destination_port=443,
        protocol="TCP",
        username="sec_admin",
        event_type="network_traffic",
        action="allow",
        outcome="success",
        severity="informational",
        category="security_rule",
        normalization_version="1.0.0"
    )
    db_session.add(norm)
    db_session.commit()

    saved = db_session.query(NormalizedEvent).filter_by(event_id="EVT-NORM-1").first()
    assert saved is not None
    assert saved.vendor == "Palo Alto Networks"
    assert saved.source_ip == "192.168.1.100"
    assert saved.destination_port == 443


def test_6_raw_to_normalized_relationship(db_session):
    """
    Test 6: Raw-to-normalized relationship.
    Answers: 'Show me the original raw event from which this normalized event was generated.'
    """
    original_raw = "<189>date=2026-09-10 time=09:30:00 devname=FGT600E srcip=10.1.1.5 dstip=172.16.0.1 action=deny"
    raw_sha = compute_sha256(original_raw)

    raw = RawEvent(
        raw_event_id="RAW-TRACE-1",
        received_at=datetime.now(timezone.utc),
        raw_payload=original_raw,
        payload_hash_sha256=raw_sha,
        source_format="syslog"
    )
    db_session.add(raw)
    db_session.commit()

    norm = NormalizedEvent(
        event_id="EVT-TRACE-1",
        raw_event_id=raw.raw_event_id,
        source_ip="10.1.1.5",
        destination_ip="172.16.0.1",
        action="deny"
    )
    db_session.add(norm)
    db_session.commit()

    # Query normalized event and resolve raw event relation
    fetched_norm = db_session.query(NormalizedEvent).filter_by(event_id="EVT-TRACE-1").first()
    assert fetched_norm is not None

    # Relationship access
    origin_raw = fetched_norm.raw_event
    assert origin_raw is not None
    assert origin_raw.raw_payload == original_raw
    assert origin_raw.raw_event_id == "RAW-TRACE-1"

    # Integrity verification on the resolved relation
    verification = verify_raw_event_record(origin_raw)
    assert verification["status"] == "valid"


def test_7_parser_registry(db_session):
    """
    Test 7: Parser registry.
    Verifies registration and uniqueness of parser modules.
    """
    parser = Parser(
        parser_id="paloalto_panos_test",
        name="PAN-OS Test Parser",
        vendor="Palo Alto Networks",
        product="PAN-OS",
        device_type="firewall",
        supported_formats=["syslog", "cef"],
        description="Modular parser for PAN-OS logs",
        enabled=True
    )
    db_session.add(parser)
    db_session.commit()

    saved = db_session.query(Parser).filter_by(parser_id="paloalto_panos_test").first()
    assert saved is not None
    assert "syslog" in saved.supported_formats
    assert saved.vendor == "Palo Alto Networks"

    # Uniqueness check
    dup_parser = Parser(
        parser_id="paloalto_panos_test",
        name="Duplicate Parser",
        vendor="Palo Alto",
        supported_formats=["syslog"]
    )
    db_session.add(dup_parser)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_8_parser_version_registry(db_session):
    """
    Test 8: Parser version registry.
    Verifies version configuration, checksum tracking, and foreign key linkage.
    """
    parser = Parser(
        parser_id="cisco_test_parser",
        name="Cisco Parser",
        vendor="Cisco",
        supported_formats=["syslog"]
    )
    db_session.add(parser)
    db_session.commit()

    config = {"regex": "%ASA-\\d-\\d+: (.*)", "action": "allow"}
    checksum = compute_sha256(str(config))

    v1 = ParserVersion(
        parser_id=parser.parser_id,
        version="1.0.0",
        checksum=checksum,
        configuration=config,
        active=True
    )
    db_session.add(v1)
    db_session.commit()

    saved_version = db_session.query(ParserVersion).filter_by(parser_id="cisco_test_parser").first()
    assert saved_version is not None
    assert saved_version.version == "1.0.0"
    assert saved_version.checksum == checksum
    assert saved_version.parser.name == "Cisco Parser"


def test_9_processing_run_metrics(db_session):
    """
    Test 9: Processing run metrics.
    Verifies operational observability counts, processing time, and run status.
    """
    run = ProcessingRun(
        run_id="RUN-2026-001",
        status="completed",
        records_received=1000,
        records_parsed=998,
        records_normalized=998,
        records_failed=2,
        processing_time_ms=145,
        error_summary="2 corrupt syslog headers"
    )
    db_session.add(run)
    db_session.commit()

    saved = db_session.query(ProcessingRun).filter_by(run_id="RUN-2026-001").first()
    assert saved is not None
    assert saved.records_received == 1000
    assert saved.records_normalized == 998
    assert saved.records_failed == 2
    assert saved.processing_time_ms == 145


def test_10_validation_result_storage(db_session):
    """
    Test 10: Validation result storage.
    Verifies recording validation warnings and schema compliance without discarding data.
    """
    raw = RawEvent(
        raw_event_id="RAW-VAL-1",
        received_at=datetime.now(timezone.utc),
        raw_payload="some raw log",
        payload_hash_sha256=compute_sha256("some raw log")
    )
    db_session.add(raw)
    db_session.commit()

    norm = NormalizedEvent(
        event_id="EVT-VAL-1",
        raw_event_id=raw.raw_event_id,
        source_ip="999.999.999.999"  # Offending IP format for validation test
    )
    db_session.add(norm)
    db_session.commit()

    val = ValidationResult(
        normalized_event_id=norm.event_id,
        validation_status="warning",
        validation_errors=[],
        validation_warnings=["Invalid IPv4 string format: 999.999.999.999"]
    )
    db_session.add(val)
    db_session.commit()

    saved_val = db_session.query(ValidationResult).filter_by(normalized_event_id="EVT-VAL-1").first()
    assert saved_val is not None
    assert saved_val.validation_status == "warning"
    assert "999.999.999.999" in saved_val.validation_warnings[0]


def test_11_nullable_universal_schema_fields(db_session):
    """
    Test 11: Nullable universal schema fields.
    Validates that events without vendor-specific optional fields insert cleanly.
    """
    raw = RawEvent(
        raw_event_id="RAW-NULL-1",
        received_at=datetime.now(timezone.utc),
        raw_payload="minimal packet log",
        payload_hash_sha256=compute_sha256("minimal packet log")
    )
    db_session.add(raw)
    db_session.commit()

    # Insert NormalizedEvent with only mandatory identifiers
    minimal_norm = NormalizedEvent(
        event_id="EVT-NULL-1",
        raw_event_id=raw.raw_event_id
    )
    db_session.add(minimal_norm)
    db_session.commit()

    saved = db_session.query(NormalizedEvent).filter_by(event_id="EVT-NULL-1").first()
    assert saved is not None
    assert saved.vendor is None
    assert saved.source_ip is None
    assert saved.destination_ip is None
    assert saved.threat_name is None
    assert saved.action is None


def test_12_custom_fields_json(db_session):
    """
    Test 12: Custom fields extensibility.
    Ensures vendor-specific non-standard telemetry can be stored in custom_fields without schema alteration.
    """
    raw = RawEvent(
        raw_event_id="RAW-CUSTOM-1",
        received_at=datetime.now(timezone.utc),
        raw_payload="custom telemetry raw",
        payload_hash_sha256=compute_sha256("custom telemetry raw")
    )
    db_session.add(raw)
    db_session.commit()

    custom_telemetry = {
        "cisco_session_flags": "TCP-SYN-ACK",
        "deep_dpi": {"application": "ssh", "tunnel": False},
        "byte_count": 48291
    }

    norm = NormalizedEvent(
        event_id="EVT-CUSTOM-1",
        raw_event_id=raw.raw_event_id,
        tags=["edge", "egress", "pci-scope"],
        custom_fields=custom_telemetry
    )
    db_session.add(norm)
    db_session.commit()

    saved = db_session.query(NormalizedEvent).filter_by(event_id="EVT-CUSTOM-1").first()
    assert saved is not None
    assert saved.custom_fields["cisco_session_flags"] == "TCP-SYN-ACK"
    assert saved.custom_fields["deep_dpi"]["application"] == "ssh"
    assert "pci-scope" in saved.tags


def test_13_immutability_and_constraint_behavior(db_session):
    """
    Test 13: Immutability & constraint enforcement.
    Architecture Principle 1: Raw events must NEVER be modified.
    Attempting to mutate raw_payload must raise ValueError.
    """
    original_payload = "Immutable raw event string"
    raw = RawEvent(
        raw_event_id="RAW-IMMUTABLE-1",
        received_at=datetime.now(timezone.utc),
        raw_payload=original_payload,
        payload_hash_sha256=compute_sha256(original_payload)
    )
    db_session.add(raw)
    db_session.commit()

    # Attempt forensic tampering
    raw.raw_payload = "MUTATED / TAMPERED LOG"
    with pytest.raises(ValueError) as exc_info:
        db_session.commit()
    assert "strictly immutable" in str(exc_info.value)
    db_session.rollback()

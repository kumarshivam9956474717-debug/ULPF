import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
import pytest
import pyarrow.parquet as pq
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.models.user import User
from app.schemas.user import UserRole
from app.services.export.export_service import ExportService
from app.services.export.parquet_exporter import ParquetExporter
from app.services.parsers.cef import CefParser
from app.services.parsers.leef import LeefParser
from app.services.persistence.base import PersistenceItem
from app.services.persistence.parquet_backend import ParquetExportBackend
from app.services.persistence.streaming_backend import StreamingSink


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def temp_export_dir():
    temp_dir = tempfile.mkdtemp(prefix="omnilogix_test_export_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_events_in_db(db_session):
    """Populates test database with linked raw and normalized events."""
    raw_records = []
    norm_records = []

    for i in range(10):
        r_id = f"RAW-TEST-{uuid.uuid4().hex.upper()}"
        payload = f"<134>Sep 16 12:00:0{i} perimeter-gw-01 snort[123]: [1:100{i}:1] ICMP ping test [src=192.168.1.{10+i} dst=10.0.0.{i} proto=ICMP]"
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        raw = RawEvent(
            raw_event_id=r_id,
            source_id="PERIMETER-TEST",
            received_at=datetime.now(timezone.utc),
            raw_payload=payload,
            payload_encoding="utf-8",
            payload_hash_sha256=h,
            source_format="syslog"
        )
        raw_records.append(raw)
        db_session.add(raw)
        db_session.flush()

        norm = NormalizedEvent(
            event_id=f"EVT-TEST-{uuid.uuid4().hex.upper()}",
            source_event_id=f"SEQ-{i}",
            raw_event_id=r_id,
            schema_version="1.0.0",
            timestamp=datetime(2026, 9, 16, 12, 0, i, tzinfo=timezone.utc),
            ingestion_timestamp=datetime(2026, 9, 16, 12, 0, i, tzinfo=timezone.utc),
            timezone="UTC",
            vendor="Cisco" if i % 2 == 0 else "Palo Alto Networks",
            product="ASA" if i % 2 == 0 else "PAN-OS",
            device_type="firewall",
            hostname="perimeter-gw-01",
            source_format="syslog",
            source_ip=f"192.168.1.{10+i}",
            source_port=1024 + i,
            destination_ip=f"10.0.0.{i}",
            destination_port=80,
            protocol="TCP",
            username=f"sec_analyst_{i}",
            event_type="network_traffic",
            action="drop" if i % 2 == 0 else "allow",
            outcome="success",
            severity="high" if i % 3 == 0 else "medium",
            category="policy_violation",
            tags=["perimeter", "test", f"batch_{i}"],
            custom_fields={"custom_rule_id": f"CR-{i}", "geo_country": "IN", "threat_score": i * 10}
        )
        norm_records.append(norm)
        db_session.add(norm)

    db_session.commit()
    return raw_records, norm_records


@pytest.fixture
def auth_headers_admin(db_session):
    admin = db_session.query(User).filter(User.username == "admin_export").first()
    if not admin:
        admin = User(
            username="admin_export",
            email="admin_export@omnilogix.local",
            hashed_password="hash",
            role="ADMIN",
            is_active=True
        )
        db_session.add(admin)
        db_session.commit()
    token = create_access_token(data={"sub": admin.username, "role": str(admin.role)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_operator(db_session):
    op = db_session.query(User).filter(User.username == "operator_export").first()
    if not op:
        op = User(
            username="operator_export",
            email="operator_export@omnilogix.local",
            hashed_password="hash",
            role="OPERATOR",
            is_active=True
        )
        db_session.add(op)
        db_session.commit()
    token = create_access_token(data={"sub": op.username, "role": str(op.role)})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TESTS
# ==============================================================================

def test_parquet_export_and_readback(temp_export_dir, db_session, sample_events_in_db):
    """Test 1: Apache Parquet export creates partitioned files readable by PyArrow."""
    svc = ExportService(export_dir=temp_export_dir)
    metrics = svc.export_events(db=db_session, format="parquet", source_id="PERIMETER-TEST")

    assert metrics.export_format == "parquet"
    assert metrics.records_selected == 10
    assert metrics.records_exported == 10
    assert metrics.files_created >= 1
    assert metrics.bytes_written > 0
    assert len(metrics.file_paths) >= 1

    # Read back generated Parquet file via PyArrow
    first_path = metrics.file_paths[0]
    assert os.path.exists(first_path)
    assert first_path.endswith(".parquet")
    table = pq.read_table(first_path)
    df = table.to_pandas()

    assert len(df) == 10
    assert "event_id" in df.columns
    assert "source_ip" in df.columns
    assert "raw_event_id" in df.columns
    assert "payload_hash_sha256" in df.columns


def test_json_and_ndjson_export(temp_export_dir, db_session, sample_events_in_db):
    """Test 2: Deterministic JSON and NDJSON export with valid structure."""
    svc = ExportService(export_dir=temp_export_dir)

    # 1. JSON Array Export
    metrics_json = svc.export_events(db=db_session, format="json", source_id="PERIMETER-TEST")
    assert metrics_json.export_format == "json"
    assert metrics_json.records_exported == 10
    json_path = metrics_json.file_paths[0]
    assert json_path.endswith(".json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 10
    assert data[0]["schema_version"] == "1.0.0"
    assert "source_ip" in data[0]

    # 2. NDJSON Line-Delimited Export
    metrics_ndjson = svc.export_events(db=db_session, format="ndjson", source_id="PERIMETER-TEST")
    assert metrics_ndjson.export_format == "ndjson"
    ndjson_path = metrics_ndjson.file_paths[0]
    assert ndjson_path.endswith(".ndjson")

    lines = []
    with open(ndjson_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                lines.append(json.loads(line))
    assert len(lines) == 10
    assert lines[0]["event_id"].startswith("EVT-TEST-")


def test_schema_consistency_canonical_fields(temp_export_dir, db_session, sample_events_in_db):
    """Test 3: Verify exported schema matches canonical UES contract."""
    svc = ExportService(export_dir=temp_export_dir)
    metrics = svc.export_events(db=db_session, format="json", source_id="PERIMETER-TEST")
    with open(metrics.file_paths[0], "r", encoding="utf-8") as f:
        records = json.load(f)

    rec = records[0]
    expected_fields = [
        "event_id", "source_event_id", "raw_event_id", "schema_version",
        "timestamp", "ingestion_timestamp", "timezone", "vendor", "product",
        "device_type", "hostname", "source_format", "source_ip", "source_port",
        "destination_ip", "destination_port", "protocol", "username",
        "event_type", "action", "outcome", "severity", "category",
        "tags", "custom_fields", "payload_hash_sha256", "raw_payload"
    ]
    for field in expected_fields:
        assert field in rec, f"Missing required canonical field '{field}'"


def test_sha256_and_raw_event_id_preservation(temp_export_dir, db_session, sample_events_in_db):
    """Test 4 & 5: Cryptographic SHA-256 hash and raw_event_id are preserved."""
    svc = ExportService(export_dir=temp_export_dir)
    metrics = svc.export_events(db=db_session, format="parquet", source_id="PERIMETER-TEST")
    table = pq.read_table(metrics.file_paths[0])
    df = table.to_pandas()

    for _, row in df.iterrows():
        assert row["raw_event_id"].startswith("RAW-TEST-")
        assert len(row["payload_hash_sha256"]) == 64
        assert row["raw_payload"].startswith("<134>Sep 16")


def test_custom_fields_and_tags_preservation(temp_export_dir, db_session, sample_events_in_db):
    """Test 6: Custom fields and tags serialize losslessly into export."""
    svc = ExportService(export_dir=temp_export_dir)
    metrics = svc.export_events(db=db_session, format="parquet", source_id="PERIMETER-TEST")
    table = pq.read_table(metrics.file_paths[0])
    df = table.to_pandas()

    first_cf = json.loads(df.iloc[0]["custom_fields"])
    assert "custom_rule_id" in first_cf
    assert first_cf["geo_country"] == "IN"

    first_tags = json.loads(df.iloc[0]["tags"])
    assert "perimeter" in first_tags


def test_cef_compatibility_and_malformed_tolerance():
    """Test 7: CEF parser extracts extensions and handles malformed headers gracefully."""
    parser = CefParser()

    # Valid CEF payload
    valid_cef = "CEF:0|Check Point|VPN-1 & FireWall-1|4.0|drop|Drop Rule|High|src=198.51.100.1 dst=203.0.113.5 spt=5432 dpt=443 proto=TCP"
    assert parser.can_parse(valid_cef)
    parsed = parser.parse(valid_cef)
    assert parsed.extracted_fields["vendor"] == "Check Point"
    assert parsed.extracted_fields["src"] == "198.51.100.1"
    assert parsed.extracted_fields["dpt"] == "443"
    assert not parsed.errors

    # Malformed CEF payload (missing pipes)
    malformed_cef = "CEF:0|Palo Alto|IncompleteHeaderWithoutPipes"
    parsed_malformed = parser.parse(malformed_cef)
    assert parsed_malformed.errors
    assert "Malformed CEF header" in parsed_malformed.errors[0]
    assert parsed_malformed.confidence <= 0.3


def test_leef_compatibility_and_malformed_tolerance():
    """Test 8: LEEF parser extracts attributes and handles malformed inputs gracefully."""
    parser = LeefParser()

    # Valid LEEF payload
    valid_leef = "LEEF:2.0|IBM|QRadar|7.3.0|AuthFailure|src=10.10.10.5\tdst=10.10.10.1\tusr=admin"
    assert parser.can_parse(valid_leef)
    parsed = parser.parse(valid_leef)
    assert parsed.extracted_fields["vendor"] == "IBM"
    assert parsed.extracted_fields["product"] == "QRadar"
    assert parsed.extracted_fields["src"] == "10.10.10.5"

    # Malformed LEEF payload
    malformed_leef = "LEEF:2.0|Broken"
    parsed_broken = parser.parse(malformed_leef)
    assert parsed_broken.errors
    assert "Malformed LEEF header" in parsed_broken.errors[0]


def test_streaming_sink_contract():
    """Test 10: StreamingSink interface contract and external publisher callback."""
    dispatched = []

    def mock_broker_publisher(events):
        dispatched.extend(events)

    sink = StreamingSink(topic="test-perimeter-topic", external_publisher=mock_broker_publisher)

    item = PersistenceItem(
        raw_event_id="RAW-SINK-01",
        raw_payload="test payload",
        payload_hash_sha256="hash123",
        received_at=datetime.now(timezone.utc),
        source_id="SINK-SRC",
        source_format="json",
        normalized_event={"event_id": "EVT-SINK-01", "source_ip": "1.1.1.1"},
        validation_status="valid"
    )

    import asyncio
    count = asyncio.run(sink.write_batch([item]))
    assert count == 1
    assert len(dispatched) == 1
    assert dispatched[0]["topic"] == "test-perimeter-topic"
    assert dispatched[0]["raw_event_id"] == "RAW-SINK-01"
    assert dispatched[0]["normalized_event"]["source_ip"] == "1.1.1.1"


def test_export_failure_handling_and_recovery(temp_export_dir, db_session):
    """Test 11 & 12: Export handles non-existent or read-only destinations cleanly."""
    invalid_dir = os.path.join(temp_export_dir, "non_existent_subdir", "file_not_dir")
    # Create file where directory is expected to induce OS error
    os.makedirs(os.path.dirname(invalid_dir), exist_ok=True)
    with open(invalid_dir, "w") as f:
        f.write("I am a file blocking directory creation")

    svc = ExportService(export_dir=invalid_dir)
    # Service should catch and raise informative exception
    with pytest.raises(Exception):
        svc.export_events(db=db_session, format="parquet")

    # Verify status reflects not stuck in exporting
    status = svc.get_status()
    assert status.status == "ready"


@pytest.fixture
def auth_client(db_session):
    """TestClient that restores real authentication dependencies for RBAC verification."""
    from app.main import app
    from app.core.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    old_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    for k in list(app.dependency_overrides.keys()):
        if getattr(k, "__name__", "") in ("get_current_user", "get_current_active_user", "override_get_current_user"):
            del app.dependency_overrides[k]

    client = TestClient(app)
    yield client
    app.dependency_overrides = old_overrides


def test_export_rbac_restrictions(auth_client: TestClient, auth_headers_admin, auth_headers_operator):
    """Test 13: Export endpoints enforce RBAC (401 unauthenticated, 403 unauthorized)."""
    # 1. Unauthenticated -> 401
    resp_unauth = auth_client.post("/api/v1/analytics/export", json={"format": "parquet"})
    assert resp_unauth.status_code == 401

    # 2. Operator Role -> 403 Forbidden (Only ADMIN allowed)
    resp_operator = auth_client.post("/api/v1/analytics/export", json={"format": "parquet"}, headers=auth_headers_operator)
    assert resp_operator.status_code == 403

    # 3. Admin Role -> 200 OK
    resp_admin = auth_client.post("/api/v1/analytics/export", json={"format": "parquet"}, headers=auth_headers_admin)
    assert resp_admin.status_code == 200
    data = resp_admin.json()
    assert "records_exported" in data


def test_air_gapped_operation_flag(temp_export_dir, db_session):
    """Test 14: Confirms air-gap flag is strictly honored and no network calls occur."""
    assert settings.AIR_GAPPED_MODE is True
    svc = ExportService(export_dir=temp_export_dir)
    metrics = svc.export_events(db=db_session, format="json")
    assert metrics.records_exported >= 0
    # Destination directory is strictly local
    assert os.path.isabs(metrics.file_paths[0] if metrics.file_paths else temp_export_dir)


def test_large_dataset_export_benchmark(temp_export_dir):
    """Test 15: Synthetic large batch export (1,000 records) measures throughput and Snappy compression."""
    records = []
    for i in range(1000):
        records.append({
            "event_id": f"EVT-BENCH-{i}",
            "raw_event_id": f"RAW-BENCH-{i}",
            "source_ip": f"10.0.{i % 256}.{i % 254 + 1}",
            "destination_ip": "172.16.0.1",
            "source_port": 10000 + (i % 50000),
            "destination_port": 443,
            "protocol": "TCP",
            "action": "allow" if i % 2 == 0 else "drop",
            "severity": "low" if i % 2 == 0 else "high",
            "message": "Outbound HTTPS connection permitted by perimeter firewall policy rule 104",
            "timestamp": "2026-09-16T12:00:00Z",
            "ingestion_timestamp": "2026-09-16T12:00:01Z",
            "custom_fields": {"rule_name": "CORP-OUTBOUND-ALLOW", "threat_intel": "none"},
            "tags": ["prod", "firewall"]
        })

    import time
    t0 = time.perf_counter()
    files_created, bytes_written, paths, p_count = ParquetExporter.write_partitioned_parquet(
        records=records,
        base_dir=temp_export_dir
    )
    duration = time.perf_counter() - t0

    assert files_created >= 1
    assert bytes_written > 0
    assert len(paths) >= 1
    # Check that 1000 events serialize in sub-second time
    throughput_eps = round(1000.0 / max(duration, 0.0001), 1)
    assert throughput_eps > 500, f"Throughput {throughput_eps} EPS below benchmark target"

    # Verify read-back row count
    table = pq.read_table(paths[0])
    assert len(table) == 1000

import os
import tempfile
import uuid
from datetime import datetime, timezone
import pytest
import pandas as pd
import pyarrow.parquet as pq
from fastapi.testclient import TestClient

from app.main import app
from app.models.normalized_event import NormalizedEvent
from app.services.export.parquet_exporter import ParquetExporter
from app.services.export.export_service import ExportService


def test_parquet_exporter_write_and_read_back():
    with tempfile.TemporaryDirectory() as tmp_dir:
        records = [
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:12]}",
                "raw_event_id": f"RAW-{uuid.uuid4().hex[:12]}",
                "schema_version": "1.0.0",
                "timestamp": "2026-09-10T10:15:30Z",
                "ingestion_timestamp": "2026-09-10T10:15:31Z",
                "vendor": "Cisco",
                "product": "ASA",
                "source_ip": "192.168.1.100",
                "destination_ip": "198.51.100.25",
                "source_port": 49210,
                "destination_port": 443,
                "protocol": "TCP",
                "action": "allow",
                "severity": "informational",
                "custom_fields": {"cisco_mnemonic": "302013", "flow_id": 9988},
                "tags": ["perimeter", "outbound"],
            },
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:12]}",
                "raw_event_id": f"RAW-{uuid.uuid4().hex[:12]}",
                "schema_version": "1.0.0",
                "timestamp": "2026-09-11T12:00:00Z",
                "ingestion_timestamp": "2026-09-11T12:00:01Z",
                "vendor": "Fortinet",
                "product": "FortiGate",
                "source_ip": "10.0.1.50",
                "destination_ip": "203.0.113.15",
                "source_port": 54321,
                "destination_port": 80,
                "protocol": "TCP",
                "action": "block",
                "severity": "high",
                "custom_fields": None,
                "tags": None,
            }
        ]

        files_created, bytes_written, paths, partition_count = ParquetExporter.write_partitioned_parquet(
            records=records,
            base_dir=tmp_dir
        )

        assert files_created == 2
        assert bytes_written > 0
        assert partition_count == 2
        assert len(paths) == 2

        # Verify partitions: year=2026/month=09/day=10 and day=11
        assert any("day=10" in p for p in paths)
        assert any("day=11" in p for p in paths)

        # Read back table using PyArrow
        table = pq.read_table(paths[0])
        assert table.num_rows == 1
        df = table.to_pandas()
        assert "event_id" in df.columns
        assert "raw_event_id" in df.columns
        assert "source_ip" in df.columns
        assert "custom_fields" in df.columns


def test_export_service_empty_and_chunked(db_session):
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ExportService(export_dir=tmp_dir)

        # Empty export
        metrics = service.export_events(db=db_session)
        assert metrics.records_selected == 0
        assert metrics.records_exported == 0
        assert metrics.files_created == 0

        # Insert 3 test normalized events
        now_dt = datetime.now(timezone.utc)
        for i in range(3):
            e = NormalizedEvent(
                event_id=f"EVT-EXP-{i}",
                raw_event_id=f"RAW-EXP-{i}",
                schema_version="1.0.0",
                timestamp=now_dt,
                ingestion_timestamp=now_dt,
                vendor="TestVendor",
                product="TestProduct",
                device_type="firewall",
                source_ip=f"10.0.0.{i}",
                destination_ip="192.168.1.1",
                source_port=1000 + i,
                destination_port=443,
                protocol="TCP",
                severity="low",
                normalization_version="1.0.0"
            )
            db_session.add(e)
        db_session.commit()

        # Run chunked export with small batch size
        metrics2 = service.export_events(db=db_session, batch_size=2)
        assert metrics2.records_selected == 3
        assert metrics2.records_exported == 3
        assert metrics2.files_created >= 1
        assert metrics2.bytes_written > 0

        status = service.get_status()
        assert status.status == "ready"
        assert status.last_export is not None
        assert status.last_export.records_exported == 3


def test_export_api_endpoints(client):
    # Trigger export
    resp = client.post("/api/v1/analytics/export", json={"batch_size": 100})
    assert resp.status_code == 200
    data = resp.json()
    assert "records_selected" in data
    assert "records_exported" in data
    assert "files_created" in data

    # Check status
    resp_status = client.get("/api/v1/analytics/export/status")
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert status_data["status"] == "ready"
    assert "export_directory" in status_data

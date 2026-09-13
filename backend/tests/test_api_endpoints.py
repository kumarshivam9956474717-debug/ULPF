from datetime import datetime, timezone
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.processing_run import ProcessingRun
from app.services.integrity import compute_sha256


def test_sources_api_lifecycle(client):
    """
    Test POST /api/v1/sources and GET /api/v1/sources
    """
    # 1. Create a log source
    payload = {
        "source_id": "fw-perimeter-test-01",
        "vendor": "Fortinet",
        "product": "FortiGate 100F",
        "device_type": "firewall",
        "hostname": "fg100f.corp.net",
        "source_format": "syslog",
        "description": "Perimeter gateway for branch office",
        "enabled": True
    }
    response = client.post("/api/v1/sources", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source_id"] == "fw-perimeter-test-01"
    assert data["vendor"] == "Fortinet"
    assert "id" in data

    # 2. Duplicate source_id rejected with 400
    dup_res = client.post("/api/v1/sources", json=payload)
    assert dup_res.status_code == 400

    # 3. List log sources
    list_res = client.get("/api/v1/sources")
    assert list_res.status_code == 200
    sources = list_res.json()
    assert any(s["source_id"] == "fw-perimeter-test-01" for s in sources)


def test_parsers_api_lifecycle(client):
    """
    Test POST /api/v1/parsers and GET /api/v1/parsers
    """
    payload = {
        "parser_id": "cisco_asa_custom",
        "name": "Cisco ASA Custom Parser",
        "vendor": "Cisco",
        "product": "ASA",
        "device_type": "firewall",
        "supported_formats": ["syslog"],
        "description": "Extracts Cisco ASA telemetry",
        "enabled": True,
        "initial_version": {
            "version": "1.0.0",
            "checksum": compute_sha256("{\"rule\": \"test\"}"),
            "configuration": {"pattern": "%ASA-.*"},
            "active": True
        }
    }
    response = client.post("/api/v1/parsers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["parser_id"] == "cisco_asa_custom"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == "1.0.0"

    # Duplicate rejected
    dup_res = client.post("/api/v1/parsers", json=payload)
    assert dup_res.status_code == 400

    # List parsers
    list_res = client.get("/api/v1/parsers")
    assert list_res.status_code == 200
    parsers = list_res.json()
    assert any(p["parser_id"] == "cisco_asa_custom" for p in parsers)


def test_events_traceability_api(client, db_session):
    """
    Test GET /api/v1/events/{event_id} and GET /api/v1/events/{event_id}/raw
    Answers: 'Show me the original raw event from which this normalized event was generated.'
    """
    raw_payload = "<134>Sep 10 09:30:00 asa-01 %ASA-6-302013: Built inbound TCP connection 9812 to 192.168.1.50:443"
    raw_hash = compute_sha256(raw_payload)

    raw = RawEvent(
        raw_event_id="RAW-API-TRACE-1",
        received_at=datetime.now(timezone.utc),
        raw_payload=raw_payload,
        payload_hash_sha256=raw_hash,
        source_format="syslog"
    )
    db_session.add(raw)
    db_session.commit()

    norm = NormalizedEvent(
        event_id="EVT-API-TRACE-1",
        raw_event_id=raw.raw_event_id,
        vendor="Cisco",
        source_ip="192.168.1.50",
        destination_port=443,
        action="allow"
    )
    db_session.add(norm)
    db_session.commit()

    # 1. Fetch normalized event
    res = client.get("/api/v1/events/EVT-API-TRACE-1")
    assert res.status_code == 200
    evt_data = res.json()
    assert evt_data["event_id"] == "EVT-API-TRACE-1"
    assert evt_data["vendor"] == "Cisco"
    assert evt_data["raw_event_id"] == "RAW-API-TRACE-1"
    assert evt_data["raw_event"] == raw_payload

    # 2. Trace to raw event via GET /api/v1/events/{event_id}/raw
    raw_res = client.get("/api/v1/events/EVT-API-TRACE-1/raw")
    assert raw_res.status_code == 200
    raw_data = raw_res.json()
    assert raw_data["event_id"] == "EVT-API-TRACE-1"
    assert raw_data["raw_event_id"] == "RAW-API-TRACE-1"
    assert raw_data["raw_payload"] == raw_payload
    assert raw_data["payload_hash_sha256"] == raw_hash
    assert raw_data["integrity"]["status"] == "valid"
    assert raw_data["integrity"]["is_tampered"] is False

    # 3. Non-existent event returns 404
    not_found = client.get("/api/v1/events/NON-EXISTENT-ID/raw")
    assert not_found.status_code == 404


def test_processing_run_api(client, db_session):
    """
    Test GET /api/v1/processing-runs/{run_id}
    """
    run = ProcessingRun(
        run_id="RUN-API-001",
        status="completed",
        records_received=500,
        records_parsed=500,
        records_normalized=498,
        records_failed=2,
        processing_time_ms=88
    )
    db_session.add(run)
    db_session.commit()

    res = client.get("/api/v1/processing-runs/RUN-API-001")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == "RUN-API-001"
    assert data["records_normalized"] == 498
    assert data["records_failed"] == 2

    # 404 for missing
    res_404 = client.get("/api/v1/processing-runs/DOES-NOT-EXIST")
    assert res_404.status_code == 404

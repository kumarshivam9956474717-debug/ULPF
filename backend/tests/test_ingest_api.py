def test_api_detect_format(client):
    payload = {"raw_payload": "CEF:0|Palo Alto Networks|PAN-OS|10.0|drop|Policy|5|src=10.0.0.1"}
    response = client.post("/api/v1/detect-format", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["detected_format"] == "cef"
    assert data["confidence"] > 0.8
    assert "reason" in data


def test_api_ingest_single(client):
    payload = {
        "raw_payload": '{"timestamp": "2026-09-10T09:30:00Z", "src_ip": "10.0.0.5", "dst_ip": "192.168.1.10", "action": "allow", "vendor": "Cisco"}',
        "source_id": "api-source-01"
    }
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["raw_event_id"] is not None
    assert data["normalized_event_id"] is not None
    assert data["detected_format"] == "json"
    assert data["normalized_event"]["source_ip"] == "10.0.0.5"

    # Verify traceability using Phase 2 endpoint
    trace_res = client.get(f"/api/v1/events/{data['normalized_event_id']}/raw")
    assert trace_res.status_code == 200
    trace_data = trace_res.json()
    assert trace_data["raw_event_id"] == data["raw_event_id"]
    assert trace_data["integrity"]["status"] == "valid"


def test_api_ingest_batch(client):
    payload = {
        "events": [
            '{"src_ip": "10.0.0.1", "action": "allow"}',
            '<166>Sep 10 09:30:00 asa %ASA-6-302013: test',
            'INVALID_LOG_RECORD'
        ],
        "source_id": "api-batch-01"
    }
    response = client.post("/api/v1/ingest/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_received"] == 3
    assert data["total_normalized"] == 2
    assert data["total_failed"] == 1
    assert "processing_run_id" in data

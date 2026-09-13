import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import numpy as np

from app.models.normalized_event import NormalizedEvent
from app.models.anomaly_result import AnomalyResult
from app.services.anomaly.feature_engineering import FeatureExtractor
from app.services.anomaly.detector import IsolationForestDetector
from app.services.anomaly.service import AnomalyService


def _create_mock_events(count: int) -> list[NormalizedEvent]:
    base_time = datetime(2026, 9, 10, 8, 0, 0, tzinfo=timezone.utc)
    events = []
    for i in range(count):
        # 1 outlier every 10 events
        is_outlier = (i % 10 == 0)
        e = NormalizedEvent(
            event_id=f"EVT-ANOM-{i:03d}",
            raw_event_id=f"RAW-ANOM-{i:03d}",
            schema_version="1.0.0",
            timestamp=base_time + timedelta(seconds=i * 15),
            ingestion_timestamp=base_time + timedelta(seconds=i * 15 + 1),
            vendor="Cisco" if not is_outlier else "ExoticVendor",
            product="ASA" if not is_outlier else "UnknownProduct",
            device_type="firewall",
            source_ip=f"10.0.1.{10 + (i % 5)}" if not is_outlier else "198.51.100.99",
            destination_ip="192.168.1.1" if not is_outlier else "203.0.113.88",
            source_port=40000 + i if not is_outlier else 1234,
            destination_port=443 if not is_outlier else 65530,
            protocol="tcp" if not is_outlier else "gre",
            severity="low" if not is_outlier else "critical",
            action="allow" if not is_outlier else "block",
            normalization_version="1.0.0"
        )
        events.append(e)
    return events


def test_feature_extractor():
    events = _create_mock_events(5)
    X, summaries = FeatureExtractor.extract_features(events)

    assert isinstance(X, np.ndarray)
    assert X.shape == (5, len(FeatureExtractor.FEATURE_NAMES))
    assert not np.isnan(X).any()
    assert not np.isinf(X).any()
    assert len(summaries) == 5
    assert "source_ip" in summaries[0]


def test_isolation_forest_detector():
    events = _create_mock_events(30)
    X, summaries = FeatureExtractor.extract_features(events)

    detector = IsolationForestDetector(contamination=0.1, random_state=42)
    assert not detector.is_trained

    detector.fit(X)
    assert detector.is_trained

    scores, is_anomalies, explanations = detector.predict(X, summaries)
    assert len(scores) == 30
    assert len(is_anomalies) == 30
    assert len(explanations) == 30

    # Scores should be normalized between 0.0 and 1.0
    assert (scores >= 0.0).all()
    assert (scores <= 1.0).all()

    # Outliers should have explanations
    for idx, is_anom in enumerate(is_anomalies):
        if is_anom:
            assert isinstance(explanations[idx], dict)
            assert "reasons" in explanations[idx]
            assert isinstance(explanations[idx]["reasons"], list)
            assert len(explanations[idx]["reasons"]) > 0


def test_anomaly_service_training_insufficient_data(db_session: Session):
    service = AnomalyService()
    # 5 events is below minimum of 20
    events = _create_mock_events(5)
    for e in events:
        db_session.add(e)
    db_session.commit()

    with pytest.raises(ValueError, match="Insufficient training data"):
        service.train_baseline(db_session, limit=5000)


def test_anomaly_service_end_to_end(db_session: Session):
    service = AnomalyService()
    events = _create_mock_events(25)
    for e in events:
        db_session.add(e)
    db_session.commit()

    # Train
    train_res = service.train_baseline(db_session, limit=5000)
    assert train_res.status == "trained"
    assert train_res.records_trained == 25

    # Scan & Persist
    scan_res = service.scan_events(db_session, limit=5000, persist=True)
    assert scan_res.status == "completed"
    assert scan_res.records_scanned == 25
    assert scan_res.anomalies_detected + scan_res.normal_detected == 25

    # Results query
    all_anomalies = service.get_results(db_session, is_anomaly_only=True)
    assert len(all_anomalies) == scan_res.anomalies_detected

    # Single event query
    sample_evt_id = events[0].event_id
    item = service.get_result_by_event_id(db_session, sample_evt_id)
    assert item is not None
    assert item.event_id == sample_evt_id
    assert 0.0 <= item.anomaly_score <= 1.0

    # Statistics
    stats = service.get_statistics(db_session)
    assert stats.total_scanned == 25
    assert stats.total_anomalies == scan_res.anomalies_detected
    assert stats.is_model_trained is True


def test_anomaly_api_endpoints(client: TestClient, db_session: Session):
    events = _create_mock_events(25)
    for e in events:
        db_session.add(e)
    db_session.commit()

    # 1. Train endpoint
    r_train = client.post("/api/v1/anomaly/train", json={"limit": 5000})
    assert r_train.status_code == 200
    train_data = r_train.json()
    assert train_data["status"] == "trained"
    assert train_data["records_trained"] == 25

    # 2. Scan endpoint
    r_scan = client.post("/api/v1/anomaly/scan", json={"limit": 5000, "persist": True})
    assert r_scan.status_code == 200
    scan_data = r_scan.json()
    assert scan_data["status"] == "completed"
    assert scan_data["records_scanned"] == 25

    # 3. List results
    r_results = client.get("/api/v1/anomaly/results?is_anomaly_only=false&limit=50")
    assert r_results.status_code == 200
    assert len(r_results.json()) == 25

    # 4. Get by event ID
    first_id = events[0].event_id
    r_item = client.get(f"/api/v1/anomaly/results/{first_id}")
    assert r_item.status_code == 200
    assert r_item.json()["event_id"] == first_id

    # 5. Non-existent event
    r_missing = client.get("/api/v1/anomaly/results/non-existent-id")
    assert r_missing.status_code == 404

    # 6. Statistics
    r_stats = client.get("/api/v1/anomaly/statistics")
    assert r_stats.status_code == 200
    stats = r_stats.json()
    assert stats["total_scanned"] == 25
    assert stats["is_model_trained"] is True

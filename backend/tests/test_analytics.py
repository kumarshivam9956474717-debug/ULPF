import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.normalized_event import NormalizedEvent
from app.services.analytics.service import AnalyticsService
from app.services.analytics.models import AnalyticsFilter

@pytest.fixture
def analytics_test_data(db_session: Session):
    """Seed normalized events with various timestamps, vendors, severities, IPs, and categories."""
    base_time = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)
    events = [
        NormalizedEvent(
            event_id=f"evt-test-an-{i}",
            raw_event_id=f"raw-test-an-{i}",
            schema_version="1.0.0",
            timestamp=base_time + timedelta(minutes=i * 10),
            ingestion_timestamp=base_time + timedelta(minutes=i * 10),
            vendor="cisco" if i % 2 == 0 else "fortinet",
            product="asa" if i % 2 == 0 else "fortigate",
            device_type="firewall",
            severity="critical" if i == 0 else ("high" if i < 3 else "low"),
            action="blocked" if i == 0 else "allowed",
            category="network_traffic",
            source_ip=f"192.168.1.{10 + i}",
            destination_ip="10.0.0.1",
            source_port=50000 + i,
            destination_port=443 if i % 2 == 0 else 80,
            protocol="tcp",
            normalization_version="1.0.0"
        )
        for i in range(6)
    ]
    for e in events:
        db_session.add(e)
    db_session.commit()
    return events

def test_analytics_service_queries(db_session: Session, analytics_test_data):
    filters = AnalyticsFilter()

    # Overview
    overview = AnalyticsService.get_overview(db_session, filters)
    assert overview.total_events == 6
    assert overview.events_per_minute >= 0.0

    # Timeline
    timeline = AnalyticsService.get_timeline(db_session, filters)
    assert len(timeline) >= 1
    total_timeline_counts = sum(p.count for p in timeline)
    assert total_timeline_counts == 6

    # Vendors distribution
    vendors = AnalyticsService.get_vendors(db_session, filters)
    assert len(vendors) == 2
    keys = {v.key for v in vendors}
    assert "cisco" in keys
    assert "fortinet" in keys

    # Severity distribution
    severities = AnalyticsService.get_severity(db_session, filters)
    assert len(severities) > 0

    # Top Source IPs
    top_ips = AnalyticsService.get_top_source_ips(db_session, limit=5, filters=filters)
    assert len(top_ips) == 5

    # Top Destination Ports
    top_dst_ports = AnalyticsService.get_top_destination_ports(db_session, limit=5, filters=filters)
    assert len(top_dst_ports) == 2
    ports = {str(p.item) for p in top_dst_ports}
    assert "443" in ports
    assert "80" in ports

def test_analytics_api_endpoints(client: TestClient, analytics_test_data):
    # Overview
    r_overview = client.get("/api/v1/analytics/overview")
    assert r_overview.status_code == 200
    data = r_overview.json()
    assert data["total_events"] == 6

    # Timeline
    r_timeline = client.get("/api/v1/analytics/timeline?interval=hour")
    assert r_timeline.status_code == 200
    assert isinstance(r_timeline.json(), list)

    # Vendors
    r_vendors = client.get("/api/v1/analytics/vendors")
    assert r_vendors.status_code == 200
    assert len(r_vendors.json()) == 2

    # Severity
    r_sev = client.get("/api/v1/analytics/severity")
    assert r_sev.status_code == 200

    # Categories
    r_cat = client.get("/api/v1/analytics/categories")
    assert r_cat.status_code == 200

    # Top IPs
    r_ips = client.get("/api/v1/analytics/top-ips?limit=5")
    assert r_ips.status_code == 200

    # Top Ports
    r_ports = client.get("/api/v1/analytics/top-ports?limit=5")
    assert r_ports.status_code == 200

    # Sources
    r_src = client.get("/api/v1/analytics/sources")
    assert r_src.status_code == 200

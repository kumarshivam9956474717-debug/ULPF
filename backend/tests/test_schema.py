from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas.universal_event import (
    UniversalEvent,
    SeverityLevel,
    EventAction,
    EventOutcome,
    NetworkDirection,
)


def test_minimal_universal_event():
    """
    Ensure the schema accepts minimal event data without forcing vendor-specific fields.
    Traceability and Raw preservation fields are mandatory.
    """
    event = UniversalEvent(
        raw_event_id="raw-1001",
        raw_event="<134>Sep 09 23:40:00 edge-router %LINK-3-UPDOWN: Interface GigabitEthernet0/1 changed state to up"
    )

    assert event.raw_event_id == "raw-1001"
    assert "GigabitEthernet0/1" in event.raw_event
    assert event.event_id is not None
    assert event.schema_version == "1.0.0"
    assert event.normalization_version == "1.0.0"
    assert event.ingestion_timestamp is not None
    # All optional fields must safely default to None or empty container
    assert event.source_ip is None
    assert event.destination_ip is None
    assert event.vendor is None
    assert event.tags == []
    assert event.custom_fields == {}
    assert event.severity == SeverityLevel.UNKNOWN


def test_full_perimeter_event_validation():
    """
    Ensure all 11 logical groups can be fully populated across heterogeneous vendors.
    """
    now = datetime.now(timezone.utc)
    event_data = {
        "event_id": "c1f72ef2-19bb-4286-9051-5aaae710189b",
        "source_event_id": "PAN-LOG-9812",
        "schema_version": "1.0.0",
        "timestamp": now,
        "timezone": "UTC+05:30",
        "vendor": "Palo Alto Networks",
        "product": "PAN-OS Firewall",
        "device_type": "firewall",
        "device_id": "PA-5250-PERIMETER-01",
        "hostname": "perimeter-fw01",
        "source_format": "syslog",
        "source_ip": "10.0.4.15",
        "source_port": 49152,
        "destination_ip": "198.51.100.25",
        "destination_port": 443,
        "protocol": "TCP",
        "username": "sec_operator",
        "user_id": "UID-4042",
        "authentication_method": "saml",
        "event_type": "network_traffic",
        "action": EventAction.ALLOW,
        "outcome": EventOutcome.SUCCESS,
        "severity": SeverityLevel.INFORMATIONAL,
        "category": "security_rule",
        "subcategory": "interzone_traffic",
        "interface": "ethernet1/2",
        "direction": NetworkDirection.OUTBOUND,
        "zone": "dmz_to_untrust",
        "threat_name": None,
        "threat_id": None,
        "signature_id": None,
        "rule_id": "Rule-DMZ-Egress-HTTPS",
        "message": "Traffic allowed per perimeter policy",
        "tags": ["perimeter", "egress", "pci-scope"],
        "custom_fields": {
            "nat_source_ip": "203.0.113.88",
            "session_id": 994218,
            "packets_received": 42
        },
        "raw_event_id": "raw-2002",
        "parser_id": "panos-syslog-parser",
        "parser_version": "1.2.0",
        "normalization_version": "1.0.0",
        "raw_event": "1,2026/09/09 23:40:00,001234,TRAFFIC,allow,...",
    }

    event = UniversalEvent(**event_data)
    assert event.vendor == "Palo Alto Networks"
    assert event.source_ip == "10.0.4.15"
    assert event.destination_port == 443
    assert event.action == EventAction.ALLOW
    assert event.custom_fields["session_id"] == 994218
    assert event.tags == ["perimeter", "egress", "pci-scope"]


def test_mandatory_raw_preservation():
    """
    Architecture Principle 1 & 2: Raw events must NEVER be discarded and normalized
    events MUST retain traceability. Omitting raw_event or raw_event_id must fail validation.
    """
    with pytest.raises(ValidationError) as exc_info:
        UniversalEvent(
            raw_event_id="raw-123"
            # raw_event omitted
        )
    assert "raw_event" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UniversalEvent(
            raw_event="Some raw syslog data"
            # raw_event_id omitted
        )
    assert "raw_event_id" in str(exc_info.value)


def test_port_validation():
    """
    Validate that invalid port values (>65535 or <0) raise ValidationError.
    """
    with pytest.raises(ValidationError):
        UniversalEvent(
            raw_event_id="raw-1",
            raw_event="raw log",
            source_port=70000  # Invalid port
        )

    with pytest.raises(ValidationError):
        UniversalEvent(
            raw_event_id="raw-1",
            raw_event="raw log",
            destination_port=-1  # Invalid port
        )


def test_extensibility_custom_fields():
    """
    Architecture Principle 4 & 5: Schema must support arbitrary vendor/device fields
    without breaking core schema or requiring core framework code modifications.
    """
    custom_vendor_telemetry = {
        "cisco_asa_message_code": "%ASA-6-302013",
        "tcp_flags": "ACK,PSH",
        "deep_packet_inspection": {
            "app_id": "google-workspace",
            "risk_score": 1
        }
    }

    event = UniversalEvent(
        raw_event_id="raw-3003",
        raw_event="raw log with custom vendor data",
        custom_fields=custom_vendor_telemetry
    )

    assert event.custom_fields["cisco_asa_message_code"] == "%ASA-6-302013"
    assert event.custom_fields["deep_packet_inspection"]["app_id"] == "google-workspace"

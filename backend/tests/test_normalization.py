from app.services.parsers.base import ParsedEvent
from app.services.normalization.service import NormalizationService
from app.schemas.universal_event import EventAction, SeverityLevel


def test_ip_and_port_aliases_normalization():
    # Test sourceAddress and destinationAddress mapping
    parsed = ParsedEvent(
        extracted_fields={
            "sourceAddress": "192.168.1.50",
            "destinationAddress": "10.0.0.1",
            "spt": "54321",
            "dpt": "443",
            "proto": "tcp"
        },
        parser_id="test_parser",
        source_format="cef"
    )

    event = NormalizationService.normalize_event(
        parsed=parsed,
        raw_event_id="RAW-TEST-01",
        raw_payload="test raw payload"
    )

    assert event.source_ip == "192.168.1.50"
    assert event.destination_ip == "10.0.0.1"
    assert event.source_port == 54321
    assert event.destination_port == 443
    assert event.protocol == "TCP"


def test_user_and_action_aliases_normalization():
    parsed = ParsedEvent(
        extracted_fields={
            "usrName": "admin_user",
            "act": "permitted",
            "sev": "high"
        },
        parser_id="test_parser",
        source_format="leef"
    )

    event = NormalizationService.normalize_event(
        parsed=parsed,
        raw_event_id="RAW-TEST-02",
        raw_payload="test raw payload"
    )

    assert event.username == "admin_user"
    assert event.action == EventAction.ALLOW
    assert event.severity == SeverityLevel.HIGH


def test_custom_fields_retention():
    parsed = ParsedEvent(
        extracted_fields={
            "src_ip": "10.1.1.1",
            "unrecognized_firewall_flag": "SYN_ACK_RECEIVED",
            "packet_length": 1500
        },
        parser_id="test_parser",
        source_format="syslog",
        custom_fields={"internal_dpi": {"inspected": True}}
    )

    event = NormalizationService.normalize_event(
        parsed=parsed,
        raw_event_id="RAW-TEST-03",
        raw_payload="test raw payload"
    )

    assert event.source_ip == "10.1.1.1"
    assert event.custom_fields["unrecognized_firewall_flag"] == "SYN_ACK_RECEIVED"
    assert event.custom_fields["packet_length"] == 1500
    assert event.custom_fields["internal_dpi"]["inspected"] is True

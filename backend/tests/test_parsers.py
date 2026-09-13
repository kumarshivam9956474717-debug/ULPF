from app.services.parsers.syslog import SyslogParser
from app.services.parsers.json_parser import JsonParser
from app.services.parsers.csv_parser import CsvParser
from app.services.parsers.cef import CefParser
from app.services.parsers.leef import LeefParser
from app.services.parsers.xml_parser import XmlParser


def test_syslog_parser_rfc5424():
    parser = SyslogParser()
    payload = "<165>1 2026-09-10T09:30:00Z edge-gw01 sec-app 1234 ID47 [meta@32473 srcip=\"10.0.0.1\"] Connection permitted"
    event = parser.parse(payload)
    assert event.parser_id == "syslog_generic"
    assert event.extracted_fields.get("hostname") == "edge-gw01"
    assert event.extracted_fields.get("process") == "sec-app"
    assert event.extracted_fields.get("facility") == (165 >> 3)
    assert event.extracted_fields.get("severity") == (165 & 7)
    assert "Connection permitted" in event.extracted_fields.get("message", "")


def test_syslog_parser_cisco():
    parser = SyslogParser()
    payload = "<166>Sep 10 09:30:00 asa-edge %ASA-6-302013: Built inbound TCP connection"
    event = parser.parse(payload)
    assert event.extracted_fields.get("hostname") == "asa-edge"
    assert event.extracted_fields.get("rule_id") == "%ASA-6-302013"
    assert event.custom_fields.get("cisco_mnemonic") == "302013"


def test_json_parser_flat_and_nested():
    parser = JsonParser()
    payload = '''{
        "timestamp": "2026-09-10T09:30:00Z",
        "src_ip": "192.168.1.50",
        "dst_ip": "10.0.0.1",
        "action": "allow",
        "metadata": {
            "rate_limit": 500,
            "internal_flag": true
        }
    }'''
    event = parser.parse(payload)
    assert event.parser_id == "json_generic"
    assert event.extracted_fields.get("src_ip") == "192.168.1.50"
    assert event.extracted_fields.get("action") == "allow"
    # Nested object must be preserved in custom_fields
    assert "metadata" in event.custom_fields
    assert event.custom_fields["metadata"]["rate_limit"] == 500


def test_csv_parser():
    parser = CsvParser()
    payload = "src_ip,dst_ip,proto,action\n10.0.1.1,192.168.1.1,TCP,deny"
    event = parser.parse(payload)
    assert event.parser_id == "csv_generic"
    assert event.extracted_fields.get("src_ip") == "10.0.1.1"
    assert event.extracted_fields.get("dst_ip") == "192.168.1.1"
    assert event.extracted_fields.get("action") == "deny"


def test_cef_parser():
    parser = CefParser()
    payload = "CEF:0|Palo Alto Networks|PAN-OS|10.1|drop|Drop Policy|7|src=198.51.100.10 dst=10.0.0.5 spt=51234 dpt=80 proto=TCP act=deny msg=Blocked egress"
    event = parser.parse(payload)
    assert event.parser_id == "cef_generic"
    assert event.extracted_fields.get("vendor") == "Palo Alto Networks"
    assert event.extracted_fields.get("product") == "PAN-OS"
    assert event.extracted_fields.get("src") == "198.51.100.10"
    assert event.extracted_fields.get("dst") == "10.0.0.5"
    assert event.extracted_fields.get("spt") == "51234"
    assert event.extracted_fields.get("act") == "deny"


def test_leef_parser():
    parser = LeefParser()
    payload = "LEEF:2.0|IBM|QRadar|7.4|IntrusionAlert|src=10.1.1.1\tdst=10.2.2.2\tproto=TCP\taction=block\tusrName=john_doe"
    event = parser.parse(payload)
    assert event.parser_id == "leef_generic"
    assert event.extracted_fields.get("vendor") == "IBM"
    assert event.extracted_fields.get("src") == "10.1.1.1"
    assert event.extracted_fields.get("usrName") == "john_doe"
    assert event.extracted_fields.get("action") == "block"


def test_xml_parser_safe():
    parser = XmlParser()
    payload = "<SecurityEvent vendor=\"F5\"><SourceIp>198.51.100.1</SourceIp><Action>block</Action></SecurityEvent>"
    event = parser.parse(payload)
    assert event.parser_id == "xml_generic"
    assert event.extracted_fields.get("SourceIp") == "198.51.100.1"
    assert event.extracted_fields.get("Action") == "block"


def test_xml_parser_xxe_protection():
    """
    Ensures malicious XML containing <!DOCTYPE or <!ENTITY is strictly rejected.
    """
    parser = XmlParser()
    malicious_payload = """<?xml version="1.0"?>
    <!DOCTYPE foo [
      <!ELEMENT foo ANY >
      <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
    <foo>&xxe;</foo>"""
    event = parser.parse(malicious_payload)
    assert len(event.errors) > 0
    assert "XXE protection" in event.errors[0]
    assert event.custom_fields.get("security_event") == "XXE_ATTEMPT_BLOCKED"

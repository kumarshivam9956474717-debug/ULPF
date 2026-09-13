from app.services.ingestion.detector import detect_format


def test_detect_cef_format():
    cef = "CEF:0|Check Point|VPN-1 & FireWall-1|R80.40|drop|Drop Security Rule|High|src=198.51.100.77 dst=10.0.1.25"
    res = detect_format(cef)
    assert res.detected_format == "cef"
    assert res.confidence >= 0.85


def test_detect_leef_format():
    leef = "LEEF:1.0|IBM|QRadar|5.4|IntrusionAlert|src=198.51.100.40\tdst=10.0.0.12\tproto=TCP"
    res = detect_format(leef)
    assert res.detected_format == "leef"
    assert res.confidence >= 0.85


def test_detect_json_format():
    json_data = '{"timestamp": "2026-09-10T09:30:00Z", "src_ip": "10.0.0.1", "action": "allow"}'
    res = detect_format(json_data)
    assert res.detected_format == "json"
    assert res.confidence >= 0.95


def test_detect_xml_format():
    xml_data = '<?xml version="1.0"?><SecurityEvent><SourceIp>10.0.0.1</SourceIp><Action>block</Action></SecurityEvent>'
    res = detect_format(xml_data)
    assert res.detected_format == "xml"
    assert res.confidence >= 0.90


def test_detect_syslog_rfc5424():
    syslog_5424 = "<165>1 2026-09-10T09:30:00.000Z mymachine.example.com evntslog - ID47 [exampleSDID@32473 iut=\"3\"] BOMAn application event log entry"
    res = detect_format(syslog_5424)
    assert res.detected_format == "syslog"
    assert res.confidence >= 0.90


def test_detect_syslog_rfc3164():
    syslog_3164 = "<134>Sep 10 09:30:00 gateway01 firewall: connection closed"
    res = detect_format(syslog_3164)
    assert res.detected_format == "syslog"
    assert res.confidence >= 0.90


def test_detect_syslog_cisco():
    cisco = "Sep 10 09:30:00 asa %ASA-6-302013: Built inbound TCP connection 9812 for outside:198.51.100.25/54321"
    res = detect_format(cisco)
    assert res.detected_format == "syslog"
    assert res.confidence >= 0.80


def test_detect_csv_format():
    csv_data = "timestamp,src_ip,dst_ip,proto,action\n2026-09-10T09:30:00Z,10.0.0.1,10.0.0.2,TCP,allow\n2026-09-10T09:30:01Z,10.0.0.3,10.0.0.4,UDP,deny"
    res = detect_format(csv_data)
    assert res.detected_format == "csv"
    assert res.confidence >= 0.80


def test_detect_unknown_format():
    unknown = "completely unformatted random telemetry payload without signature"
    res = detect_format(unknown)
    assert res.detected_format == "unknown"
    assert res.confidence < 0.50

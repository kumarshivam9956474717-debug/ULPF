import json
from app.core.database import SessionLocal, engine, Base
from app.models.log_source import LogSource
from app.models.parser import Parser, ParserVersion
from app.services.integrity import compute_sha256


def seed_database(db=None):
    """
    Seeds development database with:
    - 3 perimeter log sources
    - 3 modular parsers
    - 2 parser versions
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # 1. Seed 3 Log Sources
        sources_data = [
            {
                "source_id": "cisco-asa-edge-01",
                "vendor": "Cisco",
                "product": "ASA 5585-X",
                "device_type": "firewall",
                "hostname": "asa-edge-01.corp.local",
                "source_format": "syslog",
                "description": "Edge perimeter firewall for DMZ and egress traffic",
                "enabled": True,
            },
            {
                "source_id": "panos-ngfw-hq-01",
                "vendor": "Palo Alto Networks",
                "product": "PA-5250",
                "device_type": "firewall",
                "hostname": "panos-hq.corp.local",
                "source_format": "syslog",
                "description": "Core headquarters perimeter NGFW with Threat Prevention",
                "enabled": True,
            },
            {
                "source_id": "fortigate-utm-branch-01",
                "vendor": "Fortinet",
                "product": "FortiGate 600E",
                "device_type": "firewall",
                "hostname": "fg-branch-01.corp.local",
                "source_format": "syslog",
                "description": "Branch office perimeter UTM and VPN gateway",
                "enabled": True,
            },
        ]

        for s in sources_data:
            existing = db.query(LogSource).filter(LogSource.source_id == s["source_id"]).first()
            if not existing:
                src = LogSource(**s)
                db.add(src)

        db.flush()

        # 2. Seed 3 Parsers
        parsers_data = [
            {
                "parser_id": "cisco_asa_syslog",
                "name": "Cisco ASA Syslog Parser",
                "vendor": "Cisco",
                "product": "ASA",
                "device_type": "firewall",
                "supported_formats": ["syslog"],
                "description": "Extracts Cisco ASA %ASA-X-XXXXXX messages into Universal Event Schema.",
                "enabled": True,
            },
            {
                "parser_id": "paloalto_panos_traffic",
                "name": "Palo Alto PAN-OS Traffic Parser",
                "vendor": "Palo Alto Networks",
                "product": "PAN-OS",
                "device_type": "firewall",
                "supported_formats": ["syslog", "cef"],
                "description": "Extracts PAN-OS CSV syslog traffic and threat logs.",
                "enabled": True,
            },
            {
                "parser_id": "fortinet_fortios_utm",
                "name": "Fortinet FortiOS UTM Parser",
                "vendor": "Fortinet",
                "product": "FortiOS",
                "device_type": "firewall",
                "supported_formats": ["syslog"],
                "description": "Extracts Fortinet key-value format syslog events.",
                "enabled": True,
            },
        ]

        for p in parsers_data:
            existing = db.query(Parser).filter(Parser.parser_id == p["parser_id"]).first()
            if not existing:
                parser_obj = Parser(**p)
                db.add(parser_obj)

        db.flush()

        # 3. Seed 2 Parser Versions for cisco_asa_syslog
        v1_config = {
            "format": "syslog",
            "regex": r"^%ASA-(?P<severity>\d)-(?P<msg_code>\d+):\s+(?P<message>.*)$",
            "mappings": {
                "302013": {"action": "allow", "event_type": "network_traffic"},
                "106023": {"action": "deny", "event_type": "security_violation"}
            }
        }
        v1_checksum = compute_sha256(json.dumps(v1_config, sort_keys=True))

        v2_config = {
            "format": "syslog",
            "regex": r"^%ASA-(?P<severity>\d)-(?P<msg_code>\d+):\s+(?P<message>.*)$",
            "mappings": {
                "302013": {"action": "allow", "event_type": "network_traffic"},
                "106023": {"action": "deny", "event_type": "security_violation"},
                "710001": {"action": "drop", "event_type": "packet_filter"}
            },
            "extract_identity": True
        }
        v2_checksum = compute_sha256(json.dumps(v2_config, sort_keys=True))

        versions_data = [
            {
                "parser_id": "cisco_asa_syslog",
                "version": "1.0.0",
                "checksum": v1_checksum,
                "configuration": v1_config,
                "active": False,
            },
            {
                "parser_id": "cisco_asa_syslog",
                "version": "1.1.0",
                "checksum": v2_checksum,
                "configuration": v2_config,
                "active": True,
            },
        ]

        for v in versions_data:
            existing = db.query(ParserVersion).filter(
                ParserVersion.parser_id == v["parser_id"],
                ParserVersion.version == v["version"]
            ).first()
            if not existing:
                ver_obj = ParserVersion(**v)
                db.add(ver_obj)

        db.commit()
        print("Database successfully seeded with 3 log sources, 3 parsers, and 2 parser versions.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_database()

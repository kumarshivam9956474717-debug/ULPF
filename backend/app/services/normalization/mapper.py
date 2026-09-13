from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union
import dateutil.parser
from app.schemas.universal_event import SeverityLevel, EventAction, EventOutcome, NetworkDirection

# Centralized field alias lookup dictionary
FIELD_ALIASES: Dict[str, str] = {
    # Network - Source IP
    "src_ip": "source_ip",
    "source_ip": "source_ip",
    "src": "source_ip",
    "sourceaddress": "source_ip",
    "sourceaddressip": "source_ip",
    "srcip": "source_ip",
    "saddr": "source_ip",
    "c_ip": "source_ip",
    "c-ip": "source_ip",
    "client_ip": "source_ip",

    # Network - Destination IP
    "dst_ip": "destination_ip",
    "destination_ip": "destination_ip",
    "dst": "destination_ip",
    "destinationaddress": "destination_ip",
    "destinationaddressip": "destination_ip",
    "dstip": "destination_ip",
    "daddr": "destination_ip",
    "cs_ip": "destination_ip",
    "cs-ip": "destination_ip",
    "server_ip": "destination_ip",

    # Network - Ports
    "src_port": "source_port",
    "source_port": "source_port",
    "spt": "source_port",
    "srcport": "source_port",
    "sourceport": "source_port",
    "c_port": "source_port",
    "client_port": "source_port",

    "dst_port": "destination_port",
    "destination_port": "destination_port",
    "dpt": "destination_port",
    "dstport": "destination_port",
    "destinationport": "destination_port",
    "cs_port": "destination_port",
    "server_port": "destination_port",

    # Protocol
    "proto": "protocol",
    "protocol": "protocol",
    "transport": "protocol",
    "ip_proto": "protocol",

    # User Identity
    "username": "username",
    "user": "username",
    "usrname": "username",
    "duser": "username",
    "suser": "username",
    "src_user": "username",
    "dst_user": "username",
    "user_name": "username",
    "account": "username",
    "actor": "username",

    "user_id": "user_id",
    "uid": "user_id",
    "userid": "user_id",

    "auth_method": "authentication_method",
    "authentication_method": "authentication_method",

    # Action & Outcome
    "act": "action",
    "action": "action",
    "decision": "action",
    "operation": "action",

    "outcome": "outcome",
    "result": "outcome",
    "status": "outcome",

    # Severity
    "sev": "severity",
    "severity": "severity",
    "priority": "severity",
    "level": "severity",

    # Taxonomy
    "event_type": "event_type",
    "type": "event_type",
    "cat": "category",
    "category": "category",
    "subcat": "subcategory",
    "subcategory": "subcategory",

    # Host & Source Device
    "host": "hostname",
    "hostname": "hostname",
    "shost": "hostname",
    "dhost": "hostname",
    "devname": "hostname",
    "device_name": "hostname",
    "dvchost": "hostname",

    "device_id": "device_id",
    "dvcid": "device_id",
    "dvc": "device_id",

    "vendor": "vendor",
    "product": "product",
    "device_type": "device_type",

    # Network Context
    "interface": "interface",
    "in_interface": "interface",
    "out_interface": "interface",
    "direction": "direction",
    "zone": "zone",
    "src_zone": "zone",
    "dst_zone": "zone",

    # Threat & Rules
    "threat_name": "threat_name",
    "threat": "threat_name",
    "attack": "threat_name",
    "threat_id": "threat_id",
    "signature_id": "signature_id",
    "sig_id": "signature_id",
    "rule_id": "rule_id",
    "rule": "rule_id",
    "policy_id": "rule_id",

    # Timestamp & Message
    "timestamp": "timestamp",
    "time": "timestamp",
    "rt": "timestamp",
    "event_time": "timestamp",
    "log_time": "timestamp",

    "message": "message",
    "msg": "message",
    "details": "message",
    "reason": "message",
}

# Standardized Action Normalizer
ACTION_MAP = {
    "allow": EventAction.ALLOW,
    "allowed": EventAction.ALLOW,
    "accept": EventAction.ACCEPT,
    "accepted": EventAction.ACCEPT,
    "permit": EventAction.ALLOW,
    "permitted": EventAction.ALLOW,
    "pass": EventAction.ALLOW,
    "block": EventAction.BLOCK,
    "blocked": EventAction.BLOCK,
    "drop": EventAction.DROP,
    "dropped": EventAction.DROP,
    "deny": EventAction.DENY,
    "denied": EventAction.DENY,
    "reject": EventAction.DENY,
    "rejected": EventAction.DENY,
    "alert": EventAction.ALERT,
    "alerted": EventAction.ALERT,
    "reset": EventAction.RESET,
    "reset-both": EventAction.RESET,
    "reset-client": EventAction.RESET,
    "reset-server": EventAction.RESET,
    "authenticate": EventAction.AUTHENTICATE,
    "modify": EventAction.MODIFY,
}

# Standardized Outcome Normalizer
OUTCOME_MAP = {
    "success": EventOutcome.SUCCESS,
    "successful": EventOutcome.SUCCESS,
    "passed": EventOutcome.SUCCESS,
    "ok": EventOutcome.SUCCESS,
    "true": EventOutcome.SUCCESS,
    "fail": EventOutcome.FAILURE,
    "failed": EventOutcome.FAILURE,
    "failure": EventOutcome.FAILURE,
    "error": EventOutcome.FAILURE,
    "false": EventOutcome.FAILURE,
}

# Standardized Severity Normalizer
SEVERITY_MAP = {
    "emergency": SeverityLevel.CRITICAL,
    "alert": SeverityLevel.CRITICAL,
    "critical": SeverityLevel.CRITICAL,
    "crit": SeverityLevel.CRITICAL,
    "0": SeverityLevel.CRITICAL,
    "1": SeverityLevel.CRITICAL,
    "2": SeverityLevel.CRITICAL,
    "error": SeverityLevel.HIGH,
    "err": SeverityLevel.HIGH,
    "high": SeverityLevel.HIGH,
    "3": SeverityLevel.HIGH,
    "warning": SeverityLevel.MEDIUM,
    "warn": SeverityLevel.MEDIUM,
    "medium": SeverityLevel.MEDIUM,
    "med": SeverityLevel.MEDIUM,
    "4": SeverityLevel.MEDIUM,
    "notice": SeverityLevel.LOW,
    "low": SeverityLevel.LOW,
    "5": SeverityLevel.LOW,
    "informational": SeverityLevel.INFORMATIONAL,
    "info": SeverityLevel.INFORMATIONAL,
    "6": SeverityLevel.INFORMATIONAL,
    "debug": SeverityLevel.INFORMATIONAL,
    "7": SeverityLevel.INFORMATIONAL,
}


def normalize_field_name(raw_key: str) -> str:
    """Normalizes raw key to UES canonical attribute name or returns stripped lower key."""
    clean = raw_key.strip().lower().replace(" ", "_").replace("-", "_")
    return FIELD_ALIASES.get(clean, raw_key.strip())


def normalize_action(raw_action: Any) -> Optional[EventAction]:
    if raw_action is None:
        return None
    val = str(raw_action).strip().lower()
    return ACTION_MAP.get(val, EventAction.UNKNOWN)


def normalize_outcome(raw_outcome: Any) -> Optional[EventOutcome]:
    if raw_outcome is None:
        return None
    val = str(raw_outcome).strip().lower()
    return OUTCOME_MAP.get(val, EventOutcome.UNKNOWN)


def normalize_severity(raw_severity: Any) -> SeverityLevel:
    if raw_severity is None:
        return SeverityLevel.UNKNOWN
    val = str(raw_severity).strip().lower()
    # If numeric severity from CEF (0-10)
    try:
        num = float(val)
        if num >= 8.0:
            return SeverityLevel.CRITICAL
        elif num >= 6.0:
            return SeverityLevel.HIGH
        elif num >= 4.0:
            return SeverityLevel.MEDIUM
        elif num >= 1.0:
            return SeverityLevel.LOW
        elif num >= 0.0:
            return SeverityLevel.INFORMATIONAL
    except ValueError:
        pass
    return SEVERITY_MAP.get(val, SeverityLevel.UNKNOWN)


def normalize_port(raw_port: Any) -> Optional[int]:
    if raw_port is None:
        return None
    try:
        p = int(str(raw_port).strip())
        if 0 <= p <= 65535:
            return p
    except (ValueError, TypeError):
        pass
    return None


def normalize_timestamp(raw_time: Any) -> Optional[datetime]:
    """Parses date/time strings or epoch timestamps into UTC datetime."""
    if raw_time is None:
        return None
    if isinstance(raw_time, datetime):
        if raw_time.tzinfo is None:
            return raw_time.replace(tzinfo=timezone.utc)
        return raw_time

    if isinstance(raw_time, (int, float)):
        # Check milliseconds vs seconds
        if raw_time > 1e11:
            return datetime.fromtimestamp(raw_time / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(raw_time, tz=timezone.utc)

    s = str(raw_time).strip()
    try:
        dt = dateutil.parser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

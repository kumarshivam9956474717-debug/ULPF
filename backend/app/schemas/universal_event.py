from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SeverityLevel(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class EventAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    DROP = "drop"
    ALERT = "alert"
    RESET = "reset"
    DENY = "deny"
    ACCEPT = "accept"
    AUTHENTICATE = "authenticate"
    MODIFY = "modify"
    UNKNOWN = "unknown"


class EventOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class NetworkDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    LATERAL = "lateral"
    UNKNOWN = "unknown"


class UniversalEvent(BaseModel):
    """
    Universal Event Schema (UES) for Perimeter Network Logs.
    Vendor-agnostic, extensible, lossless, analytics-ready schema.
    Designed to represent events from any perimeter security device
    (Firewalls, IDPS, WAF, Proxies, VPN Gateways, Routers).
    """

    # 1. Identity
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier assigned to the normalized event."
    )
    source_event_id: Optional[str] = Field(
        default=None,
        description="Original identifier from the log source if present."
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Version of the Universal Event Schema applied."
    )

    # 2. Time
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Time the event occurred on the originating device."
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the raw event was ingested into ULPF."
    )
    timezone: Optional[str] = Field(
        default="UTC",
        description="Originating device timezone or offset (e.g., UTC, +05:30)."
    )

    # 3. Source Device
    vendor: Optional[str] = Field(
        default=None,
        description="Perimeter device vendor (e.g., Cisco, Palo Alto, Fortinet, Check Point)."
    )
    product: Optional[str] = Field(
        default=None,
        description="Product family or model (e.g., ASA, PAN-OS, FortiGate)."
    )
    device_type: Optional[str] = Field(
        default=None,
        description="Role classification: firewall, ids, ips, proxy, vpn, router, switch."
    )
    device_id: Optional[str] = Field(
        default=None,
        description="Unique hardware or logical identifier for the perimeter device."
    )
    hostname: Optional[str] = Field(
        default=None,
        description="Hostname or reporting perimeter gateway name."
    )
    source_format: Optional[str] = Field(
        default=None,
        description="Format of incoming raw log: syslog, cef, leef, json, w3c, csv."
    )

    # 4. Network
    source_ip: Optional[str] = Field(
        default=None,
        description="Originating IPv4 or IPv6 address."
    )
    source_port: Optional[int] = Field(
        default=None,
        ge=0,
        le=65535,
        description="Originating Layer 4 port number (0-65535)."
    )
    destination_ip: Optional[str] = Field(
        default=None,
        description="Target destination IPv4 or IPv6 address."
    )
    destination_port: Optional[int] = Field(
        default=None,
        ge=0,
        le=65535,
        description="Target Layer 4 port number (0-65535)."
    )
    protocol: Optional[str] = Field(
        default=None,
        description="Transport or application protocol: TCP, UDP, ICMP, TLS, HTTP, DNS."
    )

    # 5. User Identity
    username: Optional[str] = Field(
        default=None,
        description="Authenticated account or actor associated with the network session."
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Enterprise or directory user identifier."
    )
    authentication_method: Optional[str] = Field(
        default=None,
        description="Authentication mechanism: radius, tacacs, kerberos, ldap, mfa, local."
    )

    # 6. Event Classification
    event_type: Optional[str] = Field(
        default=None,
        description="High-level category: network_traffic, authentication, threat, configuration."
    )
    action: Optional[Union[EventAction, str]] = Field(
        default=None,
        description="Action performed: allow, block, drop, alert, reset, deny."
    )
    outcome: Optional[Union[EventOutcome, str]] = Field(
        default=None,
        description="Result of transaction: success, failure, unknown."
    )
    severity: Optional[Union[SeverityLevel, str]] = Field(
        default=SeverityLevel.UNKNOWN,
        description="Normalized severity: informational, low, medium, high, critical."
    )
    category: Optional[str] = Field(
        default=None,
        description="Taxonomy category (e.g., malware, dos, policy_violation, access)."
    )
    subcategory: Optional[str] = Field(
        default=None,
        description="Granular taxonomy subcategory (e.g., port_scan, brute_force)."
    )

    # 7. Network Context
    interface: Optional[str] = Field(
        default=None,
        description="Physical or virtual network interface (e.g., eth0, gigabitethernet0/1)."
    )
    direction: Optional[Union[NetworkDirection, str]] = Field(
        default=None,
        description="Traffic flow direction: inbound, outbound, internal, lateral."
    )
    zone: Optional[str] = Field(
        default=None,
        description="Security zone (e.g., DMZ, untrusted, internal, management)."
    )

    # 8. Threat / Security Context
    threat_name: Optional[str] = Field(
        default=None,
        description="Name of detected vulnerability, attack, or signature."
    )
    threat_id: Optional[str] = Field(
        default=None,
        description="Unique threat or CVE identifier if applicable."
    )
    signature_id: Optional[str] = Field(
        default=None,
        description="Vendor or Snort/Suricata signature identifier."
    )
    rule_id: Optional[str] = Field(
        default=None,
        description="Security policy or firewall rule identifier triggered."
    )

    # 9. Additional Data & Flexibility
    message: Optional[str] = Field(
        default=None,
        description="Descriptive message or vendor log header explanation."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorization labels for analytics queries."
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Vendor-specific or non-standard key-value attributes preserved."
    )

    # 10. Traceability & Lineage
    raw_event_id: str = Field(
        ...,
        description="Foreign key / pointer to the unmodified raw event record."
    )
    parser_id: Optional[str] = Field(
        default=None,
        description="Identifier of the parser module utilized."
    )
    parser_version: Optional[str] = Field(
        default="1.0.0",
        description="Version of the parsing logic applied."
    )
    normalization_version: str = Field(
        default="1.0.0",
        description="Version of normalization mapping applied."
    )

    # 11. Raw Preservation (Lossless guarantee)
    raw_event: str = Field(
        ...,
        description="Verbatim, unmodified raw log string exactly as ingested."
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "event_id": "4b684da5-67c4-4d8d-bf84-cb9ebbf597a8",
                "source_event_id": "90210",
                "schema_version": "1.0.0",
                "timestamp": "2026-09-09T23:45:00Z",
                "ingestion_timestamp": "2026-09-09T23:45:01Z",
                "timezone": "UTC",
                "vendor": "Palo Alto Networks",
                "product": "PAN-OS",
                "device_type": "firewall",
                "device_id": "PA-5250-HQ-01",
                "hostname": "fw-hq-edge",
                "source_format": "syslog",
                "source_ip": "192.168.1.50",
                "source_port": 54322,
                "destination_ip": "203.0.113.10",
                "destination_port": 443,
                "protocol": "TCP",
                "username": "jdoe",
                "user_id": "USR-8821",
                "authentication_method": "mfa",
                "event_type": "network_traffic",
                "action": "allow",
                "outcome": "success",
                "severity": "informational",
                "category": "web_browsing",
                "subcategory": "ssl",
                "interface": "ethernet1/1",
                "direction": "outbound",
                "zone": "trust",
                "threat_name": None,
                "threat_id": None,
                "signature_id": None,
                "rule_id": "Default-Outbound-Access",
                "message": "Session closed normally",
                "tags": ["perimeter", "hq", "egress"],
                "custom_fields": {
                    "bytes_sent": 4520,
                    "bytes_received": 12050
                },
                "raw_event_id": "raw-0001",
                "parser_id": "panos-traffic-v1",
                "parser_version": "1.0.0",
                "normalization_version": "1.0.0",
                "raw_event": "Sep  9 23:45:00 fw-hq-edge 1,2026/09/09 23:45:00,001234,TRAFFIC,drop,..."
            }
        }
    )


class RawEventTraceabilityResponse(BaseModel):
    event_id: str = Field(..., description="Normalized event identifier")
    raw_event_id: str = Field(..., description="Unique raw event identifier")
    source_id: Optional[str] = None
    received_at: datetime
    raw_payload: str
    payload_encoding: str
    payload_hash_sha256: str
    source_format: Optional[str] = None
    ingestion_batch_id: Optional[str] = None
    created_at: datetime
    integrity: Dict[str, Any] = Field(..., description="SHA-256 integrity verification status")

    model_config = ConfigDict(from_attributes=True)

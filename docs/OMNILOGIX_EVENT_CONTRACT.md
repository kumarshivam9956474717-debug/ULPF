# OmniLogix Standardized Event Contract

**Universal Log Pre-processing Framework (ULPF)**  
**Smart India Hackathon 2026 — Problem Statement SIH26156 (NTRO)**  
*Universal Event Schema (UES) Specification & Downstream Interoperability Contract*

---

## 1. Purpose of the Event Contract

The OmniLogix Event Contract establishes a formal, vendor-agnostic data specification for perimeter security telemetry. It guarantees that regardless of whether a log originated from a Cisco firewall, Palo Alto gateway, Check Point appliance, Fortinet edge device, or custom perimeter sensor:

1. Downstream SIEMs, analytical pipelines, and data lakes consume a **predictable, canonical schema**.
2. **Zero information is lost**: Unmapped or proprietary vendor fields are retained in structured `custom_fields`.
3. **Forensic defensibility is mathematically verifiable**: Every normalized event maintains an unbroken cryptographic pointer to its originating raw bytes.

---

## 2. The Lineage & Traceability Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. INBOUND RAW LOG                                                     │
│    "<165>1 2026-09-15T10:15:30Z edge-gw fw 49152 ID47 [drop src=1.2.3.4]"│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. CRYPTOGRAPHIC IMMUTABILITY ANCHOR                                  │
│    • Compute SHA-256: 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d6...  │
│    • Generate unique Raw ID: RAW-A1B2C3D4E5F678901234567890ABCDEF     │
│    • Store in raw_events table (lossless, immutable, append-only)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. DETERMINISTIC PARSING & NORMALIZATION                               │
│    • Format Detection: Syslog RFC 5424                                 │
│    • Parser Extraction: Key-Value pairs mapped to UES Attributes       │
│    • Schema Validation: Enum bounds, port validation, IP format checks  │
│    • Generate Normalized Event ID: EVT-0987654321FEDCBA1234567890ABCDEF│
│    • Set Foreign Key: raw_event_id = RAW-A1B2C3D4E5F678901234567890ABCDEF│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. DOWNSTREAM EXPORT REPRESENTATION (Parquet / JSON / Streaming)       │
│    • Embeds canonical UES fields                                       │
│    • Embeds raw_event_id pointer                                       │
│    • Embeds payload_hash_sha256 digest                                 │
│    • Embeds verbatim raw_payload                                       │
│    • Serializes custom_fields and tags without schema disruption       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Canonical Universal Event Schema (UES) Specification

Every normalized event conforms to the following 11 logical attribute groups defined in [`backend/app/schemas/universal_event.py`](file:///e:/SIH%202026/ULPF/backend/app/schemas/universal_event.py):

### Group 1: Identity & Schema Metadata
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `event_id` | `string` (UUID) | **Yes** | Universally unique identifier assigned to the normalized event. |
| `source_event_id` | `string` | No | Original event sequence or record identifier from the source appliance. |
| `schema_version` | `string` | **Yes** | Version of the canonical schema applied (default: `"1.0.0"`). |

### Group 2: Temporal Coordinates
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `timestamp` | `datetime` (ISO 8601 UTC) | No | Time the event occurred on the originating perimeter device. |
| `ingestion_timestamp` | `datetime` (ISO 8601 UTC) | **Yes** | UTC timestamp when the raw wire bytes were accepted into OmniLogix. |
| `timezone` | `string` | No | Originating device timezone offset (e.g., `"UTC"`, `"+05:30"`). |

### Group 3: Source Device Context
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `vendor` | `string` | No | Perimeter appliance vendor (e.g., `"Cisco"`, `"Palo Alto Networks"`, `"Fortinet"`). |
| `product` | `string` | No | Product model or software family (e.g., `"ASA"`, `"PAN-OS"`, `"FortiGate"`). |
| `device_type` | `string` | No | Architectural role: `"firewall"`, `"ids"`, `"ips"`, `"proxy"`, `"vpn"`, `"router"`. |
| `device_id` | `string` | No | Unique hardware serial or logical cluster node identifier. |
| `hostname` | `string` | No | Reporting hostname or Fully Qualified Domain Name (FQDN). |
| `source_format` | `string` | No | Detected wire format: `"syslog"`, `"cef"`, `"leef"`, `"json"`, `"keyvalue"`. |

### Group 4: Network Session Attributes
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `source_ip` | `string` (IPv4/IPv6) | No | Originating source IP address. |
| `source_port` | `integer` (0–65535) | No | Originating Layer 4 port number. |
| `destination_ip` | `string` (IPv4/IPv6) | No | Target destination IP address. |
| `destination_port` | `integer` (0–65535) | No | Target Layer 4 service port number. |
| `protocol` | `string` | No | Transport or application protocol: `"TCP"`, `"UDP"`, `"ICMP"`, `"TLS"`, `"DNS"`. |

### Group 5: Identity & Authentication
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `username` | `string` | No | Authenticated account or actor initiating the network transaction. |
| `user_id` | `string` | No | Enterprise directory identifier (e.g., LDAP DN, Active Directory SID). |
| `authentication_method` | `string` | No | Authentication protocol: `"radius"`, `"tacacs"`, `"kerberos"`, `"ldap"`, `"mfa"`. |

### Group 6: Event Taxonomy & Classification
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `event_type` | `string` | No | High-level category: `"network_traffic"`, `"authentication"`, `"threat"`. |
| `action` | `string` (Enum) | No | Canonical action: `"allow"`, `"block"`, `"drop"`, `"alert"`, `"reset"`, `"deny"`. |
| `outcome` | `string` (Enum) | No | Transaction result: `"success"`, `"failure"`, `"unknown"`. |
| `severity` | `string` (Enum) | **Yes** | Normalized severity: `"informational"`, `"low"`, `"medium"`, `"high"`, `"critical"`. |
| `category` | `string` | No | Taxonomy category (e.g., `"malware"`, `"dos"`, `"policy_violation"`). |
| `subcategory` | `string` | No | Fine-grained taxonomy tag (e.g., `"port_scan"`, `"brute_force"`). |

### Group 7: Network Topology Context
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `interface` | `string` | No | Physical/virtual ingress or egress interface (e.g., `"gigabitethernet0/1"`). |
| `direction` | `string` (Enum) | No | Flow direction: `"inbound"`, `"outbound"`, `"internal"`, `"lateral"`. |
| `zone` | `string` | No | Security zone boundary (e.g., `"DMZ"`, `"untrusted"`, `"management"`). |

### Group 8: Threat & Security Intelligence
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `threat_name` | `string` | No | Name of vulnerability, malware signature, or exploit. |
| `threat_id` | `string` | No | CVE identifier or threat tracking code. |
| `signature_id` | `string` | No | Snort, Suricata, or vendor-specific rule signature number. |
| `rule_id` | `string` | No | Firewall access-list or security rule name/number. |

### Group 9: Descriptive & Extensible Data
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `message` | `string` | No | Descriptive event summary or vendor log message body. |
| `tags` | `array of string` | **Yes** | Categorization tags for SIEM indexing. |
| `custom_fields` | `object` (key-value) | **Yes** | Lossless preservation of unmapped vendor attributes. |

### Group 10: Traceability & Processing Provenance
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `raw_event_id` | `string` | **Yes** | Foreign key linking this record directly to `raw_events.raw_event_id`. |
| `parser_id` | `string` | No | Identifier of parser utilized (e.g., `"syslog_cisco"`, `"cef_generic"`). |
| `parser_version` | `string` | **Yes** | Version of parsing logic applied (default: `"1.0.0"`). |
| `normalization_version` | `string` | **Yes** | Version of normalization rules applied (default: `"1.0.0"`). |

### Group 11: Lossless Raw Payload Anchor
| Field Name | Type | Required | Description |
|:---|:---|:---:|:---|
| `raw_event` | `string` | **Yes** | Exact verbatim inbound log string as received over the network. |
| `payload_hash_sha256` | `string` (Hex) | **Yes** | SHA-256 cryptographic digest of the raw wire payload. |

---

## 4. Downstream Export Representation

When serialized for downstream systems:
* **Parquet:** Primitive types are mapped to native PyArrow datatypes (`timestamp[us, tz=UTC]`, `int32`, `string`). Complex nested dictionaries (`custom_fields`, `tags`) are serialized as deterministic JSON strings to ensure zero Parquet schema evolution failures.
* **JSON / NDJSON:** Emitted as UTF-8 newline-delimited JSON objects with sorted keys, ISO 8601 timestamps, and zero credentials or secrets.
* **StreamingSink:** Dispatched as in-memory message envelopes containing topic, raw event pointers, SHA-256 digest, validation status, and normalized dictionary.

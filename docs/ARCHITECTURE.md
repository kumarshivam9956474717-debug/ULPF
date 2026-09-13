# Universal Log Pre-processing Framework (ULPF)
## System Architecture & Technical Specification

**Project:** Universal Log Pre-processing Framework (ULPF)  
**Smart India Hackathon 2026** | **Problem Statement:** `SIH26156`  
**Organization:** National Technical Research Organisation (NTRO)  
**Theme:** Blockchain & Cybersecurity  
**Deployment Profile:** Strictly Air-Gapped / 100% Offline Capable  

---

## 1. System Overview

Perimeter security infrastructures (NGFWs, edge routers, WAFs, IDPS, VPN gateways) generate immense quantities of security events in disparate, proprietary, and unstandardized syntax:
- Cisco Syslog (`%ASA-6-302013`, `%FTD-4-430002`)
- Fortinet Key-Value (`type="traffic" subtype="forward" devname="FGT"`)
- Palo Alto CSV (`TRAFFIC,drop,...`)
- ArcSight Common Event Format (CEF)
- IBM Log Event Extended Format (LEEF)
- Raw JSON & XML payloads

The **Universal Log Pre-processing Framework (ULPF)** is an open, vendor-agnostic, resilient, and air-gapped log pre-processing and supervisory intelligence framework. It provides bit-for-bit verbatim raw log preservation, deterministic format classification, modular parsing, canonical Universal Event Schema (UES) normalization, offline statistical threat analytics, and multi-entity supervisory governance with 100% lossless bi-directional traceability.

---

## 2. High-Level Architecture & Data Flow

```text
Log Sources (Firewalls, Routers, Proxies, WAFs, IDPS)
         │
         ├─── Syslog UDP (Port 1514 / 514)
         ├─── Syslog TCP / RFC 6587 (Port 1514 / 514)
         ├─── Syslog TLS 1.2+ (Port 16514 / 6514)
         └─── REST Batch Ingestion API (`POST /api/v1/ingest`)
         │
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & INTEGRITY STAGE                                         │
│ - Verbatim raw payload capture                                         │
│ - Cryptographic SHA-256 digest computation (`raw_sha256`)              │
│ - Bounded asynchronous FIFO queue with backpressure protection         │
│ - Worker pool for non-blocking concurrent ingestion                    │
│ - Immutable record persistence in `raw_events` table                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. FORMAT DETECTION & SOURCE RESOLUTION                                │
│ - Deterministic regex/token heuristics (RFC 5424/3164, CEF, LEEF,      │
│   JSON, CSV, XML, Key-Value)                                           │
│ - Confidence scoring (0.0 to 1.0) & fallback to "unknown"              │
│ - Automatic Log Source resolution (IP, Hostname, Entity assignment)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. MODULAR PARSER ENGINE & NO-CODE ONBOARDING                          │
│ - Static Parsers: Cisco ASA/FTD, Fortinet FortiOS, Palo Alto PAN-OS,   │
│   CEF, LEEF, JSON, CSV, Safe XML (XXE protected)                       │
│ - Dynamic Onboarding: ConfigurableParser loaded from `log_mapping_     │
│   profiles` for unknown vendor formats without code modification       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. UNIVERSAL EVENT SCHEMA (UES) NORMALIZATION                          │
│ - Canonical mapping into 11 logical telemetry groups                   │
│ - Non-nullable Foreign Key pointer (`raw_event_id` ──▶ `raw_events.id`) │
│ - Schema validation via Pydantic v2                                    │
│ - Immutable record persistence in `normalized_events` table            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 5. AIR-GAPPED ANALYTICS & SUPERVISORY INTELLIGENCE                     │
│ - Columnar Parquet export with Snappy compression (PyArrow / Pandas)   │
│ - Unsupervised anomaly detection (Local Scikit-Learn Isolation Forest) │
│ - Source health classification (HEALTHY, DEGRADED, SUSPICIOUS, SILENT) │
│ - 8-Capability Dimension evaluation & multi-CSE peer benchmarking      │
│ - Forensic Evidence Chain with cryptographic SHA-256 verification      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 6. OPERATIONAL INTERFACES & AUDITING                                   │
│ - React 18 / TypeScript SPA: 1-Click SIH Demonstration Workspace,      │
│   Events Explorer, No-Code Onboarding UI, Security Analytics Dashboard │
│ - FastAPI OpenAPI / Swagger interactive documentation                  │
│ - Partitioned Apache Parquet filesystem storage (`data/processed/`)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Framework Components

### 3.1 Network Transport & Ingestion Engine (`backend/app/services/syslog/`)
- **Syslog UDP Listener (`udp_listener.py`):** High-speed asynchronous UDP socket handling RFC 3164 (BSD) and RFC 5424 datagrams with oversized packet guards (`SYSLOG_MAX_MESSAGE_BYTES=65536`).
- **Syslog TCP Listener (`tcp_listener.py`):** Streaming TCP server supporting both newline-delimited framing and RFC 6587 octet-counted framing (`<length> <message>`), with per-connection idle timeouts and connection limits (`SYSLOG_TCP_CONNECTION_LIMIT=100`).
- **Syslog TLS Listener (`tls_listener.py`):** Mutual or server-authenticated TLS 1.2+ encrypted syslog listener.
- **Bounded Queue & Worker Pool (`manager.py`, `worker.py`):** Central `asyncio.Queue` bounded to `SYSLOG_QUEUE_MAXSIZE=10000`. Drops or logs backpressure telemetry when overloaded, protecting the server from denial-of-service memory exhaustion. Multiple worker tasks process queue items concurrently.

### 3.2 Verbatim Raw Preservation & Integrity (`backend/app/services/integrity.py`)
- **Lossless Ingestion:** The original log string is stored bit-for-bit without stripping whitespace, headers, or proprietary parameters into `raw_events.raw_payload`.
- **Cryptographic Hash:** A SHA-256 cryptographic digest is computed immediately upon receipt (`raw_events.raw_sha256`).
- **Audit Recalculation:** Every retrieval of a raw log (`GET /api/v1/events/{id}/raw`) recalculates the SHA-256 hash in real time and verifies that `computed_sha256 == stored_sha256`, proving zero tampering.

### 3.3 Universal Event Schema (UES) (`backend/app/models/normalized_event.py`, `schemas/universal_event.py`)
The UES standardizes perimeter telemetry into 11 canonical groups:

| Group | Key Fields | Purpose |
|---|---|---|
| **1. Identity** | `event_id` (UUIDv4), `source_event_id`, `schema_version` | Unique tracking & schema versioning |
| **2. Time** | `timestamp`, `ingestion_timestamp` (UTC), `timezone` | Temporal ordering & ingestion latency |
| **3. Source Device** | `vendor`, `product`, `device_type`, `device_id`, `hostname`, `source_format` | Originating network asset |
| **4. Network** | `source_ip`, `source_port`, `destination_ip`, `destination_port`, `protocol` | 5-tuple network transport identifiers |
| **5. User Identity** | `username`, `user_id`, `authentication_method` | Identity & access context |
| **6. Taxonomy** | `event_type`, `action` (allow/block/drop/alert/reset), `outcome`, `severity`, `category` | Standardized operational decision |
| **7. Network Context**| `interface`, `direction` (inbound/outbound/internal), `zone` | Boundary topology context |
| **8. Threat & Security**| `threat_name`, `threat_id`, `signature_id`, `rule_id` | IDS/IPS threat telemetry |
| **9. Extensibility** | `message`, `tags`, `custom_fields` (extensible JSON dict) | Vendor-specific raw attributes preserved |
| **10. Traceability** | `raw_event_id` (FK), `parser_id`, `parser_version`, `normalization_version` | Complete lineage to raw source |
| **11. Raw Preservation**| `raw_event` (verbatim log payload) | Bit-for-bit forensic reproduction |

### 3.4 No-Code Log Onboarding Engine (`backend/app/services/onboarding/`)
Integrates unknown vendor log formats without modifying Python code:
1. **Structure Analyzer (`structure_analyzer.py`):** Automatically infers envelope format (JSON, delimited, key-value, syslog-wrapped) and delimiter characters.
2. **Type Inference Engine (`type_inference.py`):** Uses regex and semantic checkers to detect IPv4/IPv6, ports, timestamps, actions, severities, and hostnames.
3. **Field Mapping Suggester (`field_mapper.py`):** Matches candidate keys against `FIELD_ALIASES` dictionary to propose UES group targets with confidence scores.
4. **Interactive Simulation (`mapping_validator.py`):** Non-mutating test execution over sample logs displaying sample normalized outputs and unmapped field warnings.
5. **Configurable Parser (`configurable_parser.py`):** Persisted `LogMappingProfile` records loaded dynamically into `ParserRegistry` at runtime.

### 3.5 Columnar Analytics Export (`backend/app/services/export/`)
- **PyArrow & Pandas Columnar Pipeline:** Exports normalized UES tables into Snappy-compressed Apache Parquet format.
- **Directory Partitioning:** `data/processed/year=YYYY/month=MM/day=DD/events-[uuid].parquet`
- **Streaming Batch Chunker:** Primary key pagination (`ULPF_EXPORT_BATCH_SIZE=10000`) prevents memory exhaustion on massive datasets.

### 3.6 Offline Anomaly Detection & Supervisory Intelligence (`backend/app/services/`)
- **Offline Machine Learning:** Local `scikit-learn` `IsolationForest` running on 9-dimensional numerical feature tensors extracted from normalized events (hour of day, port numbers, protocol encoding, severity level, action encoding).
- **Explainability Generator:** Produces deterministic, human-readable rationales (`reasons: [...]`) for every flagged anomaly.
- **Multi-CSE Supervisory Intelligence (`services/supervisory/`):**
  - **8 Capability Dimensions:** Evaluates Alert Hygiene, Investigation Rigor, Escalation Responsiveness, Log Source Availability, Telemetry Completeness, Peer Alignment, Investigation Diversity, and Volume Stability.
  - **Execution Gaps:** Detects fast closures (<10s), repeated unmitigated alerts, and unescalated criticals.
  - **Negative-Space Indicators:** Identifies missing event types, silent sources, and unmapped fields.
  - **Peer Benchmarking:** Normalizes activity across Critical Sector Entities (CSEs) using non-judgmental terminology.
  - **Bi-Directional Evidence Chain:** 6-tier cryptographic drill-down: Entity Assessment ──▶ Indicator ──▶ Normalized Event ──▶ Raw Event ──▶ Verbatim Payload ──▶ SHA-256 Hash Verification.

---

## 4. Frontend Architecture & Communication

- **Framework:** React 18 with TypeScript compiled via Vite.
- **Styling:** Vanilla CSS & Tailwind utility tokens implementing a cybersecurity dark theme.
- **API Client (`frontend/src/services/api.ts`):** Strictly typed async fetch client utilizing relative `/api/v1/` endpoints.
- **Proxy Configuration:**
  - **Development Mode:** Vite dev server proxies `/api` requests to `http://localhost:8000`.
  - **Production Mode:** Nginx reverse proxy routes `/api/` to `http://ulpf-backend:8000/api/` and serves static assets with HTML5 client-side pushState fallback (`try_files $uri $uri/ /index.html`).

---

## 5. Security & Air-Gapped Boundary Controls

```text
                       AIR-GAPPED FACILITY BOUNDARY
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   Incoming Syslog Streams (UDP/TCP 1514, TLS 16514)                     │
│                             │                                          │
│                             ▼                                          │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                      ULPF DOCKER NETWORK                       │   │
│   │                                                                │   │
│   │  [ulpf-frontend:80] ◄── Reverse Proxy ──► [ulpf-backend:8000] │   │
│   │                                                   │            │   │
│   │                                            SQLAlchemy ORM      │   │
│   │                                                   ▼            │   │
│   │                                            [ulpf-db:5432]      │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ZERO Outbound Internet Calls                                         │
│   ZERO Cloud LLM / External AI APIs                                    │
│   ZERO Telemetry Reporting                                             │
│   Cryptographic SHA-256 Event Immutability                             │
│   XXE Protected XML Parsers (`<!ENTITY` prohibited)                    │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Zero External Communication:** Neither backend nor frontend initiates outbound WAN network requests.
2. **Defensive Parsing:** XML parsers explicitly prohibit DTD external entities (`XXE_PROHIBITED_RE`), preventing XML External Entity attacks.
3. **Bounded Processing:** Regular expressions are constructed to prevent polynomial or catastrophic backtracking (ReDoS).
4. **Least-Privilege Isolation:** Docker containers run on an isolated bridge network (`ulpf-network`) exposing only explicitly required ports.

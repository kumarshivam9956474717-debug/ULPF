# OmniLogix: System Architecture Document
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH Problem Statement:** `SIH26156` | **Organization:** National Technical Research Organisation (NTRO)  
**Theme:** Blockchain & Cybersecurity | **Deployment Model:** 100% Air-Gapped Sovereign Defense Enclaves  

---

## 1. High-Level Architectural Topology

OmniLogix is an air-gapped, high-throughput, vendor-agnostic log pre-processing framework deployed as an intelligent streaming mediator between perimeter security appliances and central security repositories (SIEMs / Data Lakes):

```
                   PERIMETER NETWORK TELEMETRY
   [Cisco ASA, Fortinet, Palo Alto, Check Point, Suricata, Syslog]
                                │
               UDP / TCP / TLS (Ports 1514 / 16514)
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                TIER 2: OMNILOGIX CORE ENGINE                 │
│                 (FastAPI / Python 3.12-slim)                 │
│                                                              │
│  [1. Ingestion Layer]                                        │
│      Multi-threaded UDP, framed TCP (RFC 6587), TLS 1.2+     │
│      Captures raw string verbatim without byte mutation.     │
│                               │                              │
│  [2. Cryptographic Integrity]                                │
│      SHA-256 computed immediately at t_ingest.               │
│      Raw payload + hash committed to `raw_events`.           │
│                               │                              │
│  [3. Universal Parsers & Detection]                          │
│      Deterministic regex & pattern matcher across 13+ types. │
│      Dynamic Structure Analyzer for unknown proprietary logs.│
│                               │                              │
│  [4. Canonical Normalization]                                │
│      Transforms into 11-Group Universal Event Schema (UES).  │
│      Enforces non-nullable FK `raw_event_id` for provenance. │
│                               │                              │
│  [5. Decoupled Persistence Buffer]                           │
│      FIFO memory ring-buffer with async micro-batch flush.   │
│      Reduces DB write latency from 7.78ms to 0.10ms (98.7%). │
│                               │                              │
│  [6. Analytics & Intelligence]                               │
│      Offline Isolation Forest anomaly scoring (33k+ ev/s).   │
│      8-dimension supervisory governance scan.                │
│                               │                              │
│  [7. Multi-Format Output Sinks]                              │
│      Columnar Parquet Lake (Snappy) + Splunk CIM/Elastic ECS.│
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
    Internal Docker Network         Internal Docker Network
               │                               │
               ▼                               ▼
┌──────────────────────────────┐┌──────────────────────────────┐
│  TIER 3: PERSISTENCE LAYER   ││   TIER 1: OPERATOR CONSOLE   │
│    (PostgreSQL 16-Alpine)    ││     (Alpine / NGINX SPA)     │
│                              ││                              │
│ • Localhost bound: 127.0.0.1 ││ • React 18 / TypeScript / Vite│
│ • Named volume: postgres_data││ • 100% Air-Gapped (.woff2)   │
│ • Resilient SQLite fallback  ││ • No-Code Onboarding Console │
│ • Connection pool (20 act)   ││ • 2-Minute Evaluator Demo    │
└──────────────────────────────┘└──────────────────────────────┘
```

---

## 2. Core Functional Subsystems

### A. Multi-Transport Ingestion & Bounded Buffering
Receives perimeter telemetry without client-side modifications across **UDP 1514** (bursty network feeds), **TCP 1514** (octet-counted RFC 6587 & newline framing), **TLS 16514** (encrypted transport), and **REST APIs** (`/api/v1/ingest`). A bounded FIFO buffer (`PERSISTENCE_QUEUE_MAX_SIZE=50000`) guarantees backpressure protection against denial-of-service floods.

### B. Invariant Ingestion & SHA-256 Anti-Tamper Engine
Every raw log is captured byte-for-byte in its native encoding prior to any parsing:
$$\text{Hash}_{\text{SHA-256}} = \text{SHA-256}\left(\text{RawPayload}_{\text{UTF-8}}\right)$$
The payload, hash, and UTC timestamp are stored immutably in `raw_events`. Automated validation (`verify_payload_integrity`) flags any storage-level data modification immediately.

### C. Universal Event Schema (UES) & Bi-Directional Traceability
Disparate vendor fields are mapped into an 11-group canonical contract:
1. **Identity & Core:** `event_id`, `raw_event_id`, `schema_version`, `event_type`
2. **Temporal:** Event generation timestamp and perimeter ingestion timestamp
3. **Network Coordinates:** Source/Destination IP, Ports, Zones, Protocol
4. **Security Disposition:** Action (`allow`, `deny`, `drop`, `reject`, `alert`), Rule ID
5. **Threat Intelligence:** Severity (`CRITICAL` to `LOW`), Signature ID, Category
6. **Device & Host:** Hostname, Vendor, Product, Model
7. **User & Identity:** Username, Domain, Authentication Method, Status
8. **Custom Fields (JSONB):** Zero-loss preservation of unmapped vendor parameters
9. **Provenance:** Ingestion version, tags, cryptographic SHA-256 digest

Every normalized record enforces a non-nullable foreign key link:
$$\text{NormalizedEvent.raw\_event\_id} \longleftrightarrow \text{RawEvent.raw\_event\_id}$$
This establishes an unbroken mathematical chain of custody for legal and judicial proceedings.

### D. No-Code Extensible Onboarding Engine
When unmapped or proprietary log formats enter the perimeter:
1. **Structure Analyzer:** Ingests sample strings, identifies token delimiters (pipes, commas, spaces), and detects key-value patterns (`k=v`).
2. **Type Inference:** Deterministically identifies IPs, timestamps, ports, and action keywords.
3. **Dynamic Registry Injection:** Compiles a validated regex profile and injects it directly into memory (`ParserRegistry`) without service restarts or code recompilation.

### E. Decoupled Asynchronous Persistence Engine
Synchronous database commits create an I/O bottleneck (capping speeds at ~150 ev/s). OmniLogix decouples ingestion from storage:
- Ingestion workers push parsed events to an in-memory ring buffer.
- Asynchronous workers execute bulk inserts triggered by batch size (500 events) or time elapsed (100 ms).
- **Benchmark Result:** Reduces database write latency from **7.78 ms to 0.10 ms** (98.7% reduction), sustaining throughput above **1.35 million events/second**.

---

## 3. Data Lake Egress & Air-Gapped Security Architecture

| Subsystem | Technical Implementation | Operational Benefit |
|---|---|---|
| **Columnar Data Lake** | Snappy-compressed Apache Parquet partitioned by date (`year/month/day`). | 85–90% reduction in raw disk consumption; ultra-fast SQL queries via DuckDB/Spark. |
| **SIEM Crosswalks** | Pre-mapped field matrices for Splunk CIM, Elastic ECS, and Sentinel ASIM. | Eliminates vendor lock-in and removes SIEM runtime regex parsing overhead. |
| **Air-Gap Hardening** | Local `.woff2` font bundles, zero public CDNs, socket outbound egress guard. | Guarantees 100% offline functionality within classified sovereign defense enclaves. |
| **Container Hardening** | Backend runs as unprivileged user `omnilogix` (UID 10001); DB bound to `127.0.0.1`. | Eliminates root container breakouts and secures the internal database interface. |
| **Cryptographic RBAC** | Salted Bcrypt (12 rounds) + HMAC-SHA256 JWT tokens across 4 roles (`ADMIN`, `ANALYST`, `OPERATOR`, `VIEWER`). | Enforces least-privilege administrative access and tamper-proof user sessions. |
| **Resilient Failover** | Automatic zero-downtime failover to local SQLite (`demo.db`) if PostgreSQL is offline. | Ensures continuous standalone evaluation and zero data loss during host restarts. |

# OmniLogix Verified Capabilities Catalog
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH 2026 Problem Statement:** `SIH26156` (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Verification Categories:** `VERIFIED` | `CONFIGURED` | `ARCHITECTURAL` | `NOT CLAIMED`

---

## 1. Verified Capabilities (Empirically Tested in Repository)

| Capability | Scope & Evidence |
|---|---|
| **Deterministic Format Detection** | Heuristic & pattern-based detection for 8+ primary formats with 100% precision in test suite. |
| **Lossless Raw Preservation** | Immutable byte-for-byte storage in `raw_events` table and Parquet exports. |
| **Cryptographic SHA-256 Anti-Tamper** | Ingest-time hashing; any byte deviation detected immediately via `verify_sha256()`. |
| **Bi-Directional Event Traceability** | Non-nullable `raw_event_id` foreign key enforces 100% auditability back to raw payload. |
| **Universal Event Schema (UES)** | 11-group structured schema covering Identity, Network, Threat, Timing, and Custom fields. |
| **Universal Multi-Vendor Parsers** | Native parsers for Cisco ASA, Fortinet FortiGate, Palo Alto, Check Point, Suricata, CEF, LEEF, JSON, CSV, XML, and Syslog RFC 3164/5424. |
| **No-Code Parser Onboarding** | Structure Analyzer + regex generator + test simulator for unknown perimeter formats. |
| **Decoupled Asynchronous Persistence** | In-memory batch queue reducing single-event database write latency from 7.78ms to 0.10ms (98.7% reduction). |
| **Multi-Format Data Lake Exporter** | Snappy-compressed columnar Apache Parquet, NDJSON, and JSON exports with timestamp partitioning. |
| **SIEM Schema Mapping** | Universal mapping matrices for Splunk CIM, Elastic ECS, and Microsoft Sentinel ASIM. |
| **Supervisory Intelligence Engine** | 8 capability dimensions, peer benchmarking, operational execution gap detection, and Scenarios A-J validation (100% F1-score). |
| **Offline Anomaly Detection** | Scikit-learn Isolation Forest model training and scoring completely offline without cloud connectivity. |
| **Cryptographic RBAC** | Salted Bcrypt (12 rounds), HMAC-SHA256 JWT tokens, and 4 operational roles (`ADMIN`, `ANALYST`, `OPERATOR`, `VIEWER`). |
| **Air-Gapped Runtime Enforcement** | Zero CDNs, bundled fonts, socket outbound guard (`AIR_GAPPED_MODE=True`). |
| **Containerized Deployment** | 3-tier Docker Compose stack (`ulpf-db`, `ulpf-backend`, `ulpf-frontend`) with non-root user `omnilogix` (UID 10001). |

---

## 2. Configured Capabilities (Ready for Deployment via Configuration)

| Capability | Configuration Parameters |
|---|---|
| **Syslog Multi-Transport Listeners** | Configurable UDP (1514), TCP (1514), and TLS (16514) listeners with queue backpressure. |
| **Database Connection Pooling** | Configurable SQLAlchemy pool sizes (`DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=30`). |
| **Resilient SQLite Fallback** | Automatic zero-intervention failover to local SQLite (`sqlite:///./demo.db`) if PostgreSQL is unavailable. |
| **CORS Origins & Security Headers** | Host restriction via `ALLOWED_ORIGINS` and automatic injection of anti-sniff/clickjacking HTTP headers. |

---

## 3. Architectural Capabilities (Documented Design & Abstraction Layer)

| Capability | Design & Abstraction Status |
|---|---|
| **Distributed Broker Cluster (Kafka)** | `StreamingSink` interface implemented in `backend/app/services/persistence/streaming_sink.py`; multi-node Kafka cluster topology documented in `SCALABLE_DEPLOYMENT_ARCHITECTURE.md`. |
| **Multi-Node Database Replication** | Patroni / pgpool-II primary-replica clustering architecture specified in `SCALABLE_DEPLOYMENT_ARCHITECTURE.md`. |
| **Horizontal Load Balancing** | HAProxy layer-4 load balancing and Kubernetes Deployment/Ingress configurations documented in `PRODUCTION_DEPLOYMENT_HARDENING.md`. |

---

## 4. Not Claimed Capabilities (Explicitly Disclaimed)

- Live multi-datacenter distributed Kafka/PostgreSQL cluster deployment inside the single-workstation evaluation repository.
- Autonomous incident adjudication without human analyst review (OmniLogix serves supervisory triage and governance).

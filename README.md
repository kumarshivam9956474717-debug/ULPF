# Universal Log Pre-processing Framework (ULPF)

**Smart India Hackathon 2026**  
**Problem Statement:** `SIH26156`  
**Organization:** NTRO  
**Theme:** Blockchain & Cybersecurity  
**Deployment Profile:** Strictly Air-Gapped / 100% Offline Capable  

---

## 1. Problem Statement & Background

Modern perimeter security infrastructure (NGFWs, edge routers, IDPS, VPN gateways, WAFs) produces massive volumes of security events in fragmented, proprietary, and unstructured formats:
- Cisco Syslog (`%ASA-6-302013`, `%FTD-4-430002`)
- Palo Alto CSV Syslog (`TRAFFIC`, `THREAT`)
- Fortinet Key-Value (`type="traffic" subtype="forward"`)
- ArcSight Common Event Format (CEF)
- IBM Log Event Extended Format (LEEF)
- Raw JSON & Safe XML payloads

Existing SIEM and log aggregation pipelines suffer from vendor lock-in, high processing latency, loss of original raw payload context, and dependency on external cloud services.

The **Universal Log Pre-processing Framework (ULPF)** is an open, vendor-agnostic, scalable, and air-gapped framework built to ingest, verify, normalize, and audit perimeter security logs with **100% lossless bi-directional traceability** and **cryptographic SHA-256 integrity verification**.

---

## 2. Proposed Solution

ULPF provides an end-to-end, decoupled log processing and supervisory intelligence framework:
1. **Verbatim Raw Event Preservation:** Every log is ingested and stored immutably alongside its cryptographic SHA-256 hash before any transformation occurs.
2. **Deterministic Format & Source Detection:** Automatically classifies incoming logs (RFC 5424, RFC 3164, CEF, LEEF, JSON, CSV, XML, Key-Value) with confidence scoring.
3. **Modular Parser Plugins:** Vendor-specific parsers extract attributes into a normalized staging structure without altering core framework logic.
4. **Universal Event Schema (UES):** Canonical, immutable schema organized into 11 logical groups covering identity, network, device, taxonomy, threat, and traceability.
5. **No-Code Log Onboarding Engine:** Semi-automated structural analysis and type inference for unknown perimeter log formats with human-in-the-loop preview.
6. **Air-Gapped Anomaly & Threat Detection:** Statistical modeling and unsupervised machine learning (`IsolationForest`) executing 100% locally without cloud telemetry.
7. **Multi-CSE Supervisory Intelligence:** Multi-entity governance across Critical Sector Entities (CSEs) tracking 8 capability dimensions, peer benchmarking, and forensic evidence chains.

---

## 3. Key Features

- **100% Lossless Raw Preservation:** Original payloads are preserved bit-for-bit in `raw_events`.
- **Bi-Directional Traceability:** Every `NormalizedEvent` maintains a non-nullable foreign key pointer (`raw_event_id`) to its originating raw record.
- **Cryptographic Integrity:** Automatic SHA-256 recalculation on query (`GET /api/v1/events/{id}/raw`) verifies that zero tampering occurred.
- **Strict Air-Gapped Operation:** Zero external API calls, cloud telemetry, or SaaS dependencies.
- **High-Throughput Syslog Transport:** Asynchronous UDP, TCP (newline and octet-counted framing), and TLS 1.2+ listeners with bounded queue backpressure guards.
- **Interactive SIH Demonstration Workspace:** 1-Click guided 9-step evaluation pipeline with automated scenario validation (Scenarios A through J).
- **Epistemic Data Quality Auditing:** Rigorous distinction between *No Evidence*, *Evidence of Absence*, and *Insufficient Data*.

---

## 4. System Architecture & Processing Pipeline

```text
Raw Event (Syslog / UDP / TCP / File / API)
         │
         ▼
Ingestion Stage (Verbatim raw capture + SHA-256 hash generation)
         │
         ▼
Format & Vendor Detection (RFC 5424/3164, CEF, LEEF, JSON, CSV, XML, Key-Value)
         │
         ▼
Modular Parser Plugins (Cisco, Fortinet, Palo Alto, Generic)
         │
         ▼
Universal Event Schema (UES) Normalization (11 logical telemetry groups)
         │
         ▼
Validation & Quality Audit (Schema conformance + foreign-key linkage)
         │
         ▼
Analytics & Supervisory Intelligence (Isolation Forest + 8 Capability Dimensions)
         │
         ▼
Export & Forensic Auditing (Partitioned Apache Parquet + JSON/CSV Reports)
```

---

## 5. Supported Log Formats & Vendor Examples

| Format | Vendors / Standards | Example Pattern |
|---|---|---|
| **Syslog (RFC 3164 / BSD)** | Legacy Routers & Firewalls | `<134>Sep 12 11:30:00 asa-01 %ASA-6-302013: ...` |
| **Syslog (RFC 5424)** | Modern Perimeter Systems | `<165>1 2026-09-12T11:30:00Z fw01 ASA 1234 ID47 ...` |
| **Key-Value Syslog** | Fortinet FortiOS / UTM | `date=2026-09-12 time=11:30:00 devname="FGT" srcip=10.0.1.50` |
| **CSV Syslog** | Palo Alto PAN-OS | `1,2026/09/12 11:30:00,001201000,TRAFFIC,drop,...` |
| **CEF (Common Event Format)** | ArcSight, Check Point, FTD | `CEF:0|Cisco|ASA|9.1|106023|Deny traffic|6|src=...` |
| **LEEF** | IBM QRadar / Edge Appliances | `LEEF:2.0|Vendor|Product|Version|EventID|src=...` |
| **Raw JSON** | Cloudflare Edge, WAFs, Proxies | `{"timestamp": "...", "client_ip": "...", "action": "block"}` |
| **Safe XML** | Perimeter Devices (XXE Protected)| `<event><source_ip>192.168.1.1</source_ip></event>` |

---

## 6. Technology Stack

### Backend & Core Pipeline
- **Python 3.12+**
- **FastAPI:** Async REST API framework with automated OpenAPI/Swagger documentation.
- **Pydantic v2:** High-speed schema validation and immutable UES models.
- **SQLAlchemy 2.0:** Relational ORM supporting PostgreSQL 16 and SQLite fallback.
- **Alembic:** Database migration orchestration.
- **Scikit-learn, NumPy, Pandas:** Offline statistical modeling, feature matrices, and anomaly detection.
- **Pytest & HTTPX:** Automated test suite covering unit, integration, and security tests.

### Frontend Shell
- **React 18 & TypeScript:** Strict type-safe UI architecture.
- **Vite:** Build tooling and local development server.
- **Tailwind CSS:** Cybersecurity dark/light theme.
- **React Router v6:** Client-side routing.
- **Lucide React:** Infrastructure and security iconography.

### Infrastructure & Deployment
- **Docker & Docker Compose:** Multi-service container orchestration.

---

## 7. Universal Event Schema (UES) Groups

The Universal Event Schema standardizes perimeter telemetry into 11 canonical groups:
1. **Identity:** `event_id` (UUID), `source_event_id`, `schema_version`
2. **Time:** `timestamp`, `ingestion_timestamp` (UTC), `timezone`
3. **Source Device:** `vendor`, `product`, `device_type`, `device_id`, `hostname`, `source_format`
4. **Network:** `source_ip`, `source_port`, `destination_ip`, `destination_port`, `protocol`
5. **User Identity:** `username`, `user_id`, `authentication_method`
6. **Event Taxonomy:** `event_type`, `action` (allow/block/drop/alert/reset), `outcome`, `severity`, `category`
7. **Network Context:** `interface`, `direction` (inbound/outbound/internal), `zone`
8. **Threat & Security:** `threat_name`, `threat_id`, `signature_id`, `rule_id`
9. **Additional / Extensibility:** `message`, `tags`, `custom_fields` (extensible dictionary)
10. **Traceability:** `raw_event_id` (FK), `parser_id`, `parser_version`, `normalization_version`
11. **Raw Preservation:** `raw_event` (verbatim log payload)

---

## 8. Project Structure

```text
ULPF/
├── backend/                      # FastAPI + SQLAlchemy + Pydantic backend
│   ├── alembic/                  # Database migration versions
│   ├── app/
│   │   ├── api/v1/               # REST API endpoints (health, ingest, syslog, demo, etc.)
│   │   ├── core/                 # Configuration & resilient database engine
│   │   ├── models/               # SQLAlchemy ORM models (raw_events, normalized_events, etc.)
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── services/             # Modular parsers, UES normalizer, anomaly engine
│   │   ├── utils/                # Benchmarking utilities
│   │   └── main.py               # Application entry point
│   ├── tests/                    # Pytest automated test suite (102 tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                     # React + TypeScript + Vite + Tailwind frontend
│   ├── src/
│   │   ├── components/           # Sidebar, Header, SystemStatusCard, Layout
│   │   ├── pages/                # EvaluationWorkspace, Dashboard, Ingestion, Events, etc.
│   │   ├── services/             # Type-safe API client
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
├── data/
│   ├── raw/                      # Ingested raw log staging
│   ├── processed/                # Normalized Parquet / JSON exports
│   └── synthetic/                # Synthetic benchmark datasets (Cisco, Fortinet, PA, CEF, etc.)
├── database/                     # Schema reference documentation
├── docs/                         # Architecture, verification reports, and air-gap audits
├── tools/
│   ├── run_evaluation.py         # One-command reproducible SIH evaluation runner
│   └── syslog_sender.py          # Synthetic syslog network emitter
├── docker-compose.yml            # Multi-service composition (Postgres, Backend, Frontend)
├── .env.example                  # Safe configuration template (zero credentials)
├── .gitignore                    # Complete exclusions for caches, databases, node_modules
├── LICENSE                       # MIT Open Source License
└── README.md
```

---

## 9. Deployment & Website Access

### Local Access (Development & Local Evaluation)
- **Frontend Application:** `http://localhost:5173`
- **SIH Demonstration Workspace:** `http://localhost:5173/demo`
- **Backend API & Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/v1/health`

### Public Deployment Status
- **Public Deployment:** Not Deployed (Framework designed for air-gapped on-premises enclaves)
- **Live Evaluation URL:** `To be deployed`

---

## 10. Quick Evaluation Guide (For SIH Judges)

To evaluate the complete framework locally in under 3 minutes:

### Step 1: Clone Repository
```bash
git clone <repository_url>
cd ULPF
```

### Step 2: One-Command Reproducible Evaluation
Execute the self-contained verification runner:
```bash
python tools/run_evaluation.py
```
This automatically resets the isolated evaluation environment, generates synthetic telemetry across 5 CSE entities, executes UES normalization, evaluates Scenarios A through J, and prints the validation summary.

### Step 3: Start Services Locally
**Terminal 1 — Backend:**
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Step 4: Explore the User Interface
1. Open `http://localhost:5173/demo` in your browser.
2. Click **Start Demonstration** to run the 9-step guided evaluation workflow.
3. Review **Demonstration Results — SIH Scenarios Validation (Scenarios A through J)**.
4. Explore **Events Explorer** (`/events`) to inspect 11-group UES normalization and click **Inspect** to audit the cryptographic SHA-256 raw log verification.
5. Explore **Security Analytics** (`/security-analytics`) and **Supervisory Assessment** (`/supervisory`) for multi-entity governance.

---

## 11. Running Automated Tests

Run the complete backend test suite:
```bash
cd backend
python -m pytest tests/ -v
```
**Test Results:** **102 passed, 0 failed** across all modules:
- System Health & Readiness (`test_health.py`)
- Universal Event Schema (`test_schema.py`)
- Format Detection (`test_detection.py`)
- Modular Parsers & Normalization (`test_parsers.py`, `test_normalization.py`)
- Persistence, Traceability & SHA-256 (`test_persistence.py`, `test_pipeline.py`)
- REST APIs (`test_api_endpoints.py`, `test_ingest_api.py`)
- Syslog UDP / TCP / TLS (`test_syslog_*.py`)
- Anomaly Detection & Supervisory Intelligence (`test_anomaly.py`, `test_supervisory_intelligence.py`)
- Scenario Validation Engine (`test_phase8_demo_validation.py`)

Run the frontend typecheck and production build:
```bash
cd frontend
npm run build
```
**Build Result:** `0 errors, 0 warnings` (production bundle generated cleanly).

---

## 12. Evaluation Scenarios (Scenarios A through J)

ULPF evaluates 10 operational and supervisory scenarios deterministically:

| Scenario ID | Title | Expected Entity | Expected Indicator | Validation Status |
|---|---|---|---|---|
| **Scenario_A** | High-severity alerts closed in < 10 seconds | `CSE-ALPHA-01` | `FAST_CASE_CLOSURE_WITHOUT_INVESTIGATION` | **PASS (100% Precision)** |
| **Scenario_B** | Repeated alerts from same asset without remediation | `CSE-BETA-02` | `REPEATED_ALERTS_WITHOUT_REMEDIATION` | **PASS (100% Precision)** |
| **Scenario_C** | Critical alerts without escalation evidence | `CSE-GAMMA-03` | `CRITICAL_EVENT_LACKS_ESCALATION_EVIDENCE` | **PASS (100% Precision)** |
| **Scenario_D** | Registered active log source becoming silent | `CSE-EPSILON-05` | `SILENT_LOG_SOURCE` | **PASS (100% Precision)** |
| **Scenario_E** | Critical asset missing expected telemetry | `CSE-DELTA-04` | `MISSING_EVENT_CATEGORY` | **PASS (100% Precision)** |
| **Scenario_F** | One CSE significantly deviates from peer activity | `CSE-GAMMA-03` | `PEER_ACTIVITY_DEVIATION` | **PASS (100% Precision)** |
| **Scenario_G** | Repeated/template-like investigation patterns | `CSE-ALPHA-01` | `TEMPLATE_INVESTIGATION_PATTERN` | **PASS (100% Precision)** |
| **Scenario_H** | Sudden abnormal event-volume increase | `CSE-BETA-02` | `VOLUME_SPIKE` | **PASS (100% Precision)** |
| **Scenario_I** | Sudden abnormal event-volume decrease | `CSE-EPSILON-05` | `VOLUME_DROP` | **PASS (100% Precision)** |
| **Scenario_J** | Unknown log format requiring no-code onboarding | `CSE-ALPHA-01` | `UNKNOWN_VENDOR_FORMAT` | **PASS (100% Precision)** |

---

## 13. High-Capacity Performance Benchmarks

To execute the offline high-volume performance benchmark:
```bash
python backend/app/utils/performance_benchmark.py
```

Benchmark performance summary (AMD/Intel x86_64 local hardware):
- **Raw Ingestion & SHA-256 Hash Computation:** **> 1,000,000 events/sec**
- **Offline Anomaly Detection (`IsolationForest`):** **~46,000 events/sec**
- **Supervisory Alert Prioritization:** **~200,000 events/sec**
- **8-Capability Scan Latency:** **< 0.1 ms**
- **Backend Test Suite:** **102/102 PASSED (100% pass rate)**
- **Frontend Production Build:** **0 TypeScript errors, 0 build warnings**

---

## 14. Docker Quick Start

> **Air-Gapped Notice:**  
> ULPF is designed for on-premises and air-gapped cybersecurity environments. Docker Compose provides a platform-independent deployment method for local evaluation.

### Prerequisites (Zero Local Python/Node Required)
A fresh evaluation machine requires only:
- **Git**
- **Docker Desktop** (or Docker Engine with Compose v2)
*No local installation of Python, Node.js, npm, or database servers is necessary on the host.*

### 1-Command Startup
```bash
# 1. Clone repository
git clone <repository_url>
cd ULPF

# 2. Build and start all services
docker compose up --build -d
```

### Access Endpoints
| Component | Host URL | Description |
|---|---|---|
| **Frontend UI** | `http://localhost:5173` | React 18 / TypeScript single-page application |
| **SIH Demonstration Workspace** | `http://localhost:5173/demo` | 1-Click interactive evaluation and scenario validation |
| **Backend REST API** | `http://localhost:8000` | FastAPI core service |
| **Interactive API Documentation** | `http://localhost:8000/docs` | Swagger UI (also proxied at `http://localhost:5173/docs`) |
| **Health Check & Readiness** | `http://localhost:8000/api/v1/health` | Comprehensive subsystem readiness checks |

### Ingestion Ports (Syslog Network Transport)
| Protocol | Port | Description |
|---|---|---|
| **Syslog UDP** | `1514/udp` | RFC 3164 / RFC 5424 high-speed datagram listener |
| **Syslog TCP** | `1514/tcp` | Delimited and octet-counted streaming listener |
| **Syslog TLS** | `16514/tcp` | TLS 1.2+ encrypted syslog listener |

### Stopping Services
```bash
# Graceful shutdown preserving database and volume data
docker compose down

# To clean up volumes as well (fresh re-initialization):
docker compose down -v
```

### Troubleshooting
- **Port Conflict (8000 / 5173):** Ensure no local dev servers (`uvicorn`, `vite`) are occupying ports 8000 or 5173 on the host machine before running Docker Compose.
- **Inspect Service Logs:** Run `docker compose logs -f ulpf-backend` or `docker compose logs -f ulpf-frontend` to trace initialization events.
- **Health Verification:** Check container status via `docker compose ps`. Services indicate `healthy` once their internal HTTP health checks pass.

---

## 15. Security & Air-Gapped Verification

- **Zero Cloud Egress:** Network policies enforce zero external communication. All machine learning, parsing, and analytics models execute strictly on local CPU/RAM.
- **Cryptographic Tamper-Evidence:** Any byte change in a raw event breaks the SHA-256 verification hash upon query.
- **No Hardcoded Secrets:** Managed through 12-factor `.env` files conforming to defense facility standards.
- **XXE and ReDoS Protection:** XML parsers explicitly disable entity resolution and external DTDs; regexes are bounded to prevent catastrophic backtracking.

---

## 16. Screenshots & Interface Overview

| View | Path | Description |
|---|---|---|
| **SIH Demonstration Workspace** | `/demo` | 1-Click interactive pipeline runner with Scenarios A through J validation breakdown. |
| **System Health & Architecture** | `/dashboard` | System status, ingestion pipeline throughput, and component readiness monitoring. |
| **Events Explorer & Traceability** | `/events` | Universal Event Schema inspection with cryptographic SHA-256 verification and raw log audit. |
| **No-Code Log Onboarding** | `/onboarding` | Interactive structure analysis, type inference, and field mapping for unknown vendor formats. |
| **Security Analytics & Prioritization** | `/security-analytics` | Air-gapped IsolationForest anomaly detection and contextual alert scoring. |
| **Multi-CSE Supervisory Intelligence** | `/supervisory` | 8-capability dimension evaluation, peer benchmarking, and forensic evidence chains. |

---

## 17. Known Limitations

- **Default Storage Fallback:** When PostgreSQL is not active, the system defaults to an isolated local SQLite database (`sqlite:///demo.db`). For enterprise deployments with millions of events, PostgreSQL 16 is recommended.
- **Air-Gapped Pre-bundling:** When deploying to completely isolated secure facilities without Internet access, Python wheels and npm package tarballs must be transferred via authorized physical media.

---

## 18. Team Information

- **Competition:** Smart India Hackathon (SIH) 2026
- **Problem Statement:** `SIH26156` (NTRO)
- **Theme:** Blockchain & Cybersecurity
- **Project:** Universal Log Pre-processing Framework (ULPF)
- **License:** [MIT License](LICENSE)


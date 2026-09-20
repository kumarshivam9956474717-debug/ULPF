# OmniLogix: Universal Log Pre-Processing Framework (ULPF)

**Smart India Hackathon 2026**  
**Problem Statement:** `SIH26156` (National Technical Research Organisation — NTRO)  
**Theme:** Blockchain & Cybersecurity  
**Deployment Profile:** Strictly Air-Gapped / 100% Offline Capable  
**Current Test Status:** **151/151 tests passing (100% green)**  
**Evaluation Status:** 🟢 `VERIFIED` (Single-Node Containerized Stack) / `ARCHITECTURAL` (Distributed HA)

---

## 1. What is OmniLogix?

**OmniLogix (ULPF)** is a vendor-agnostic, lossless, high-throughput perimeter log pre-processing and security telemetry framework. It ingests high-velocity raw security telemetry from firewalls, edge routers, WAFs, and IDPS devices, cryptographically preserves every raw log byte with invariant SHA-256 integrity, normalizes heterogeneous events into a canonical Universal Event Schema (UES), and exports standardized streams to downstream SIEMs (Splunk, Elastic, Sentinel) and columnar Data Lakes (Apache Parquet) in strict air-gapped defense enclaves.

---

## 2. Problem Statement Mapping (SIH26156 — NTRO)

Modern perimeter defense systems generate terabytes of fragmented, proprietary, and unstructured event streams daily. Existing SIEM ingestion pipelines suffer from:
1. **Severe Vendor Lock-in & Ingestion Tax:** SIEMs charge by ingested data volume while spending expensive CPU cycles parsing raw strings.
2. **Loss of Forensic Ground Truth:** Aggressive extraction often discards original unparsed payload context, compromising legal and investigative chains of custody.
3. **Cloud & External Telemetry Vulnerabilities:** Traditional tools rely on external CDNs, cloud licensing servers, or public fonts unsuited for air-gapped defense networks.

OmniLogix directly addresses these challenges through a standalone, air-gapped containerized processing pipeline that guarantees 100% lossless forensic traceability.

---

## 3. Key Capabilities Matrix

| Capability | Evaluation Status | Implementation & Evidence |
|---|---|---|
| **Multi-Vendor Ingestion** | `VERIFIED` | 13+ formats parsed natively (Cisco, Fortinet, Palo Alto, Check Point, Suricata, Syslog, CEF, LEEF, JSON, CSV, XML). |
| **Lossless Raw Preservation** | `VERIFIED` | Immutable raw byte storage in PostgreSQL `raw_events` and Parquet export columns. |
| **Cryptographic SHA-256 Integrity** | `VERIFIED` | Ingest-time hashing; payload alteration detected immediately via `verify_sha256()`. |
| **Bi-Directional Traceability** | `VERIFIED` | Normalized events maintain non-nullable `raw_event_id` foreign key linkage to raw records. |
| **Universal Event Schema (UES)** | `VERIFIED` | Canonical 11-group schema (Identity, Network, Host, Device, Threat, Custom, Timing). |
| **No-Code Log Onboarding** | `VERIFIED` | Interactive Structure Analyzer + regex generator for unknown perimeter streams without code changes. |
| **Decoupled Batch Persistence** | `VERIFIED` | In-memory asynchronous queue reducing write latency from 7.78ms to 0.10ms (98.7% reduction). |
| **Data Lake & SIEM Exporter** | `VERIFIED` | Snappy-compressed columnar Parquet, NDJSON, and JSON exports with Splunk CIM, Elastic ECS, and Sentinel ASIM mappings. |
| **Supervisory Intelligence & Anomaly Engine**| `VERIFIED` | 8 capability dimensions, peer benchmarking, and offline Scikit-Learn `IsolationForest` scoring. |
| **Cryptographic RBAC** | `VERIFIED` | Salted Bcrypt (12 rounds), HMAC-SHA256 JWT tokens, and 4 roles (`ADMIN`, `ANALYST`, `OPERATOR`, `VIEWER`). |
| **Strict Air-Gapped Operation** | `VERIFIED` | Zero CDNs, bundled `.woff2` fonts, socket outbound egress guard (`AIR_GAPPED_MODE=True`). |
| **Containerized Deployment** | `VERIFIED` | 3-tier Docker Compose with non-root security (`omnilogix`, UID 10001) and loopback DB binding. |
| **Multi-Broker Streaming (Kafka)** | `ARCHITECTURAL` | `StreamingSink` interface implemented; distributed cluster topology documented in `SCALABLE_DEPLOYMENT_ARCHITECTURE.md`. |
| **Multi-Node Database HA** | `ARCHITECTURAL` | Patroni / pgpool-II primary-replica clustering architecture specified in `SCALABLE_DEPLOYMENT_ARCHITECTURE.md`. |

---

## 4. Architecture Reference

```
                 PERIMETER NETWORK TELEMETRY
         (Firewalls, Edge Routers, WAFs, IDPS, Gateways)
                              │
             UDP / TCP / TLS (Ports 1514 / 16514)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       OmniLogix Stack                        │
│                                                              │
│  [1. Ingestion] Verbatim Raw Capture + Invariant SHA-256     │
│         │                                                    │
│  [2. Detection] Deterministic Format & Vendor Identification │
│         │                                                    │
│  [3. Normalization] Universal Event Schema (11 Groups)       │
│         │                                                    │
│  [4. Decoupled Buffer] High-Speed In-Memory Worker Queue     │
│         │                                                    │
│         ├────────────────────────┬─────────────────────────┐ │
│         ▼                        ▼                         ▼ │
│  [PostgreSQL 16]         [Parquet Lake]          [Streaming] │
│  (Relational Storage)   (Columnar Snappy)       (SIEM Sinks) │
│         ▲                                                    │
│         │                                                    │
│  [Frontend UI (NGINX / React 18 SPA)] ◄── Evaluator Browser  │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Supported Formats & Systems

1. **Cisco ASA NGFW:** `%ASA-3-106023`, `%ASA-6-302013` session built/teardown.
2. **Fortinet FortiGate:** Delimited key-value traffic, system, and UTM antivirus logs.
3. **Palo Alto PAN-OS:** Standard CSV traffic and threat vulnerability records.
4. **Check Point FireWall-1:** Key-value/pipe firewall drop and C2 beacon reject events.
5. **Suricata IDS/IPS:** JSON EVE network flow, port scan, and malware alerts.
6. **RFC 3164 Syslog:** BSD legacy system, auth, and router configuration logs.
7. **RFC 5424 Syslog:** Structured enterprise syslog with structured data elements.
8. **ArcSight CEF:** Common Event Format threat and brute-force records.
9. **IBM QRadar LEEF:** Log Event Extended Format perimeter authentication events.
10. **Structured JSON:** Machine-readable cloud, auth, and host security telemetry.
11. **Delimited CSV / TSV:** NetFlow and proxy access connection logs.
12. **XXE-Hardened XML:** Web Application Firewall (WAF) event streams.
13. **Unknown / Proprietary Formats:** Dynamic no-code tokenized log onboarding.

---

## 6. Technology Stack

- **Backend Core:** Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Uvicorn.
- **Data & Persistence:** PostgreSQL 16 (production), SQLite 3 (resilient zero-dependency fallback).
- **Analytics & ML:** Scikit-learn (Isolation Forest), NumPy, PyArrow (Apache Parquet Snappy).
- **Security & Cryptography:** Passlib (Bcrypt 12 rounds), Python-Jose (HMAC-SHA256 JWT), DefusedXML.
- **Frontend SPA:** React 18, TypeScript, Tailwind CSS, Vite 5, Lucide Icons, bundled fonts.
- **Orchestration:** Docker Compose v2, NGINX Alpine, Python Slim base images.

---

## 7. Setup & Installation Instructions

OmniLogix supports two primary deployment methods: **Docker Compose** (recommended for evaluators and judges, requires 0 host language installations) and **Local Native Setup** (for development without Docker, using automatic SQLite fallback).

### Prerequisites

| Component | Option A: Docker Compose | Option B: Local Native Setup |
|---|---|---|
| **Operating System** | Linux, Windows 10/11 (WSL2), macOS | Linux, Windows 10/11, macOS |
| **Container Engine** | Docker Engine 24.0+ & Compose v2.20+ | Not Required |
| **Python Runtime** | Not required on host (bundled in container) | Python 3.10+ (tested up to 3.14) |
| **Node.js Runtime** | Not required on host (bundled in NGINX SPA) | Node.js 18+ and npm |
| **Database** | PostgreSQL 16 (auto-launched via Docker) | Automatic SQLite fallback (`demo.db`) or PostgreSQL |

---

### Option A: 1-Command Docker Setup (Recommended)

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/kumarshivam9956474717-debug/ULPF.git
   cd ULPF
   ```

2. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   ```

3. **Launch the Container Stack:**
   ```bash
   docker compose up -d
   ```

4. **Access the Applications:**
   - **Web UI & Dashboard:** [http://localhost:5173](http://localhost:5173)
   - **Interactive API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Application Health Status:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

5. **Stop / Teardown Container Stack:**
   ```bash
   docker compose down
   ```

---

### Option B: Local Native Setup (Zero Docker Required)

If Docker is not running on your workstation, OmniLogix automatically falls back to an internal resilient SQLite storage engine (`sqlite:///./demo.db`):

1. **Clone the Repository & Prepare Environment:**
   ```bash
   git clone https://github.com/kumarshivam9956474717-debug/ULPF.git
   cd ULPF
   cp .env.example .env
   ```

2. **Backend Setup:**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux / macOS:
   source venv/bin/activate

   # Install dependencies
   pip install -r backend/requirements.txt

   # Start FastAPI Backend Server
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```

3. **Frontend Setup (In a New Terminal):**
   ```bash
   cd ULPF/frontend
   npm install
   npm run dev
   ```
   - Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 8. Administrator Account Setup & Credentials

OmniLogix enforces cryptographic role-based access control (RBAC). You can bootstrap the initial administrative account in two ways:

### Method 1: Interactive CLI Utility
Run the interactive user creation wizard:
```bash
python tools/create_admin.py
```
*Prompts for Username, Email, and Password, then creates a salted Bcrypt-hashed `ADMIN` account.*

### Method 2: Automatic Bootstrap via `.env`
Specify bootstrap credentials directly in your `.env` file before starting the backend:
```env
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_PASSWORD=AdminStrongPassword2026!
ADMIN_BOOTSTRAP_EMAIL=admin@omnilogix.local
```
The backend automatically provisions this user with the `ADMIN` role upon first initialization.


---

## 9. Verification & Test Commands

### 1. Master Evidence Validator (All 14 Subsystems)
```bash
python tools/final_evaluation.py
```
*Exits with code `0` when all mandatory checks pass.*

### 2. Full Backend Pytest Regression Suite
```bash
python -m pytest backend/tests -q
```
*Expected:* **151 passed, 0 failed, 1 warning (100% green)**.

### 3. Scenario Validation Runner (Scenarios A through J)
```bash
python tools/run_evaluation.py
```
*Expected:* **10 / 10 Scenarios Passed (100% Precision, 100% Recall, 100% F1-score)**.

### 4. Frontend Production Build
```bash
cd frontend && npm run build
```
*Expected:* 0 TypeScript errors, 0 bundler warnings, clean static output in `frontend/dist/`.

---

## 10. 2-Minute Judge Demo Workflow

1. Open `http://localhost:5173/demo` in your browser.
2. Click **Start Guided Demonstration**:
   - **Step 1:** Ingests 250+ multi-CSE logs across 5 Critical Sector Entities.
   - **Step 2:** Normalizes events into the 11-group UES and computes invariant SHA-256 hashes.
   - **Step 3:** Runs unsupervised Isolation Forest anomaly detection.
   - **Step 4:** Executes 8-dimension supervisory intelligence scan across 5 entities.
   - **Step 5-6:** Audits operational execution gaps and supervisory findings.
   - **Step 7:** Traces bi-directional evidence chain: Normalized Event $\leftrightarrow$ `raw_event_id` $\leftrightarrow$ SHA-256 Hash.
   - **Step 8:** Evaluator submits audit review decision.
   - **Step 9:** Exports downloadable evaluation report (JSON / CSV).
3. Visit `http://localhost:5173/onboarding` to demonstrate **No-Code Onboarding** of unknown proprietary logs without code modification.
4. Visit `http://localhost:5173/events` and click **Inspect** to verify cryptographic SHA-256 raw event anti-tamper.

---

## 11. Network Port Map

| Port | Protocol | Service | Scope | Security Consideration |
|---|---|---|---|---|
| **5173** | TCP | Frontend NGINX / Vite | External | Web dashboard and operator UI. |
| **8000** | TCP | Backend FastAPI API | External | REST API, documentation, health probe. |
| **1514** | UDP | Syslog UDP Listener | External | RFC 3164 / 5424 unencrypted syslog. |
| **1514** | TCP | Syslog TCP Listener | External | Octet-counted and newline-framed TCP syslog. |
| **16514**| TCP | Syslog TLS Listener | External | Encrypted TLS 1.2+ syslog transport. |
| **5432** | TCP | PostgreSQL Database | Loopback Only (`127.0.0.1`) | Restricted to localhost to prevent public exposure. |

---

## 12. Air-Gapped Deployment & Offline Image Transfer

OmniLogix is designed to operate completely offline. For deployment into restricted defense enclaves:

```bash
# On Internet-Connected Machine:
docker compose build
docker save postgres:16-alpine ulpf_backend:latest ulpf_frontend:latest | gzip > omnilogix_images.tar.gz

# Transfer omnilogix_images.tar.gz via approved offline media to Air-Gapped Machine:
docker load < omnilogix_images.tar.gz
docker compose up -d
```

---

## 13. Verified Performance Benchmarks

| Operation | 1,000 Events | 10,000 Events | 50,000 Events | 100,000 Events |
|---|---|---|---|---|
| **Ingestion + SHA-256 Hashing** | 1,199,904 ev/s | 1,464,043 ev/s | 1,198,808 ev/s | 1,354,059 ev/s |
| **Decoupled Batch DB Writes** | 0.10 ms/event | 0.10 ms/event | 0.10 ms/event | 0.10 ms/event |
| **Offline Isolation Forest Scoring**| 8,186 ev/s | 39,388 ev/s | 43,875 ev/s | 33,092 ev/s |
| **Priority Alert Scoring** | 152,263 ev/s | 67,792 ev/s | 199,657 ev/s | 197,547 ev/s |
| **8-Dimension Supervisory Scan** | 0.069 ms | 0.081 ms | 0.053 ms | 0.061 ms |

---

## 14. Operational Limitations & Future Roadmap

- **Single-Node vs. Distributed Clustering:** Single-node Docker deployment is `VERIFIED`. Distributed Kafka clustering and Patroni multi-node replication are `ARCHITECTURAL` and documented in `docs/SCALABLE_DEPLOYMENT_ARCHITECTURE.md`.
- **In-Memory Queue Bounds:** The persistence queue uses a 50,000-event in-memory buffer. For sustained multi-gigabit perimeter feeds over days, external Kafka message brokers are recommended.
- **Automated Adjudication Disclaimer:** OmniLogix produces supervisory intelligence and anomaly prioritization to assist human examiners; it does not claim autonomous incident adjudication without expert human review.

---

## 15. Complete Documentation Index

- **Final Evaluation Report:** [`docs/FINAL_SIH_EVALUATION_REPORT.md`](file:///e:/SIH%202026/ULPF/docs/FINAL_SIH_EVALUATION_REPORT.md)
- **Demonstration Runbook:** [`docs/DEMO_RUNBOOK.md`](file:///e:/SIH%202026/ULPF/docs/DEMO_RUNBOOK.md)
- **Architecture Specification (2-Page):** [`architecture/ARCHITECTURE_DOCUMENT.md`](file:///e:/SIH%202026/ULPF/architecture/ARCHITECTURE_DOCUMENT.md)
- **Repository Readiness Audit:** [`docs/REPOSITORY_READINESS_AUDIT.md`](file:///e:/SIH%202026/ULPF/docs/REPOSITORY_READINESS_AUDIT.md)
- **Requirement Traceability Matrix:** [`docs/FINAL_REQUIREMENT_TRACEABILITY.md`](file:///e:/SIH%202026/ULPF/docs/FINAL_REQUIREMENT_TRACEABILITY.md)
- **Verified Capabilities Catalog:** [`docs/VERIFIED_CAPABILITIES.md`](file:///e:/SIH%202026/ULPF/docs/VERIFIED_CAPABILITIES.md)
- **Known Operational Limitations:** [`docs/KNOWN_LIMITATIONS.md`](file:///e:/SIH%202026/ULPF/docs/KNOWN_LIMITATIONS.md)
- **Production Deployment Hardening:** [`docs/PRODUCTION_DEPLOYMENT_HARDENING.md`](file:///e:/SIH%202026/ULPF/docs/PRODUCTION_DEPLOYMENT_HARDENING.md)
- **Technical Architecture FAQ:** [`docs/TECHNICAL_FAQ.md`](file:///e:/SIH%202026/ULPF/docs/TECHNICAL_FAQ.md)
- **SIEM & Data Lake Integration:** [`docs/SIEM_DATA_LAKE_INTEGRATION.md`](file:///e:/SIH%202026/ULPF/docs/SIEM_DATA_LAKE_INTEGRATION.md)
- **OmniLogix Event Contract (UES):** [`docs/OMNILOGIX_EVENT_CONTRACT.md`](file:///e:/SIH%202026/ULPF/docs/OMNILOGIX_EVENT_CONTRACT.md)


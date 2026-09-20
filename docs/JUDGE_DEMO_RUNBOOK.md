# OmniLogix Judge Demo Runbook (2-Minute Walkthrough)
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH 2026 Problem Statement:** `SIH26156` (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Target Duration:** ~2 Minutes  
**Prerequisites:** Stack running via Docker Compose or local development server.

---

## 1. Quick Start (Clean Machine)

```bash
# 1. Clone repository & configure environment
git clone https://github.com/your-org/omnilogix.git
cd omnilogix
cp .env.example .env

# 2. Run master evaluation validation
python tools/final_evaluation.py

# 3. Start stack (Docker or Local)
docker compose up -d
# UI available at: http://localhost:5173
```

---

## 2. 2-Minute Step-by-Step Evaluator Script

### Stage 1: Problem & Ingestion (0:00 - 0:25)
1. **Navigate to:** `http://localhost:5173/demo` (or click **SIH Demo** in sidebar).
2. **Narration Points:**
   - *Problem:* Heterogeneous perimeter devices (Cisco, Palo Alto, Fortinet, Check Point, Suricata) emit conflicting formats (RFC 3164, RFC 5424, CEF, LEEF, Key-Value, JSON).
   - *Ingestion:* OmniLogix ingests multi-transport streams (Syslog UDP/TCP/TLS, REST API, Batch) with zero data loss.
3. **Action:** Click **"Start Guided Demonstration"** (or Step 1: **"Load Evaluation Dataset"**).
   - *Observed Outcome:* System generates and loads 250+ multi-CSE events across 5 Critical Sector Entities.

### Stage 2: Universal Processing & Raw Preservation (0:25 - 0:50)
1. **Action:** Step 2: **"Process & Normalize"**.
2. **Narration Points:**
   - *Format Detection & Normalization:* Automatically identifies syntax and maps fields to the 11-group Universal Event Schema (UES).
   - *Lossless Preservation:* Verbatim raw bytes are stored immutably alongside normalized attributes.
   - *SHA-256 Anti-Tamper:* Ingest-time cryptographic digest is computed on raw bytes.
3. **Action:** Navigate to `http://localhost:5173/events` and click **"Inspect"** on any event.
   - *Observed Outcome:* Modal displays the side-by-side comparison of normalized fields, original raw payload, and verified SHA-256 digest.

### Stage 3: Security Intelligence & Supervisory Governance (0:50 - 1:20)
1. **Action:** Step 4: **"Supervisory Assessment"**.
2. **Narration Points:**
   - *8 Capability Dimensions:* Scans ingestion coverage, escalation rigor, triage timeliness, and telemetric negative space.
   - *Deterministic Scenario Validation:* Accurately identifies Scenarios A through J (fast closures without investigation, repeat alerts, silent sources, peer deviations).
3. **Action:** Switch between `CSE-ALPHA-01` and `CSE-GAMMA-03`.
   - *Observed Outcome:* Entity risk radar charts and capability scores update dynamically.

### Stage 4: Extensibility & No-Code Onboarding (1:20 - 1:40)
1. **Action:** Navigate to `http://localhost:5173/onboarding`.
2. **Narration Points:**
   - *Extensibility:* When a new or proprietary firewall format enters the network, operators do not need developer code changes.
3. **Action:** Click **"Analyze Sample"** on the sample tokenized log.
   - *Observed Outcome:* Structure Analyzer infers delimiters, tokenizes keys/values, and previews normalized output in real-time.

### Stage 5: Enterprise Outputs & Air-Gapped Verification (1:40 - 2:00)
1. **Action:** Step 9: **"Generate Report"** in Evaluation Workspace or visit `http://localhost:5173/analytics`.
2. **Narration Points:**
   - *Outputs:* Generates Snappy-compressed Parquet columnar files for Data Lakes and mapped exports for Splunk CIM, Elastic ECS, and Microsoft Sentinel.
   - *Air-Gapped Guarantee:* Entire demonstration ran without a single external HTTP request, CDN call, or cloud API.
3. **Action:** Click **"Download Audit Report"**.
   - *Observed Outcome:* Complete evaluation findings and scenario validation records download instantly as JSON/CSV.

---

## 3. Demo Fallback & Standalone Offline Execution
If the web UI is not accessible during judging, the exact same evaluation pipeline can be run in the terminal:
```bash
python tools/run_evaluation.py
```
This prints the full 10-scenario validation breakdown with 100% precision, recall, and F1-score in ~2 seconds.

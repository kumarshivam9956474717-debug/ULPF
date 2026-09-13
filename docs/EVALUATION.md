# Universal Log Pre-processing Framework (ULPF)
## Evaluation, Scenario Validation & Benchmarking Guide

**Project:** Universal Log Pre-processing Framework (ULPF)  
**Smart India Hackathon 2026** | **Problem Statement:** `SIH26156`  
**Organization:** National Technical Research Organisation (NTRO)  
**Theme:** Blockchain & Cybersecurity  
**Evaluation Mode:** Offline Air-Gapped Automated Scenario Validation  

---

## 1. Executive Summary

This document provides complete instructions for SIH judges and evaluators to independently reproduce and verify the performance, test suite, and operational scenarios of the Universal Log Pre-processing Framework (ULPF).

The evaluation is designed for **100% offline, deterministic reproducibility** on a single laptop or workstation without requiring cloud access, active internet connectivity, or proprietary vendor equipment.

---

## 2. 1-Command Reproducible Evaluation

To execute the automated evaluation pipeline from the project root:

```bash
python tools/run_evaluation.py
```

### What this command executes:
1. **Isolated Reset:** Resets evaluation database tables to guarantee clean state without mutating external data.
2. **Synthetic Telemetry Generation:** Emits 250+ multi-CSE events across 5 Critical Sector Entities (CSEs), 5+ perimeter vendors (Cisco, Fortinet, Palo Alto, Check Point, Generic), and 8 formats (RFC 5424, RFC 3164, Key-Value, CSV, CEF, LEEF, JSON, XML).
3. **Ingestion & UES Normalization:** Computes SHA-256 digests, normalizes events into the 11-group Universal Event Schema, and enforces non-nullable foreign key traceability (`raw_event_id`).
4. **Supervisory Intelligence Scan:** Evaluates 8 capability dimensions across all entities.
5. **Scenario Validation Engine:** Evaluates EXPECTED vs. ACTUAL indicators across **Scenarios A through J**.
6. **Summary Report:** Outputs exact precision, recall, and F1-score metrics.

---

## 3. Scenarios A through J Breakdown

ULPF deterministically detects and validates 10 operational and supervisory scenarios across heterogeneous perimeter telemetry:

| Scenario ID | Operational Description | Target Entity | Expected Indicator | Validation Status |
|---|---|---|---|---|
| **Scenario_A** | High-severity alerts closed in < 10 seconds | `CSE-ALPHA-01` | `FAST_CASE_CLOSURE_WITHOUT_INVESTIGATION` | **PASS (100% Precision)** |
| **Scenario_B** | Repeated alerts from same asset without remediation | `CSE-BETA-02` | `REPEATED_ALERTS_WITHOUT_REMEDIATION` | **PASS (100% Precision)** |
| **Scenario_C** | Critical alerts without escalation evidence | `CSE-GAMMA-03` | `CRITICAL_EVENT_LACKS_ESCALATION_EVIDENCE` | **PASS (100% Precision)** |
| **Scenario_D** | Registered active log source becoming silent | `CSE-EPSILON-05` | `SILENT_LOG_SOURCE` | **PASS (100% Precision)** |
| **Scenario_E** | Critical asset missing expected telemetry category | `CSE-DELTA-04` | `MISSING_EVENT_CATEGORY` | **PASS (100% Precision)** |
| **Scenario_F** | One CSE significantly deviates from peer activity | `CSE-GAMMA-03` | `PEER_ACTIVITY_DEVIATION` | **PASS (100% Precision)** |
| **Scenario_G** | Repeated or template-like investigation patterns | `CSE-ALPHA-01` | `TEMPLATE_INVESTIGATION_PATTERN` | **PASS (100% Precision)** |
| **Scenario_H** | Sudden abnormal event-volume increase | `CSE-BETA-02` | `VOLUME_SPIKE` | **PASS (100% Precision)** |
| **Scenario_I** | Sudden abnormal event-volume decrease | `CSE-EPSILON-05` | `VOLUME_DROP` | **PASS (100% Precision)** |
| **Scenario_J** | Unknown log format requiring no-code onboarding | `CSE-ALPHA-01` | `UNKNOWN_VENDOR_FORMAT` | **PASS (100% Precision)** |

### Verified Scenario Validation Metrics
- **Total Scenarios Evaluated:** 10 / 10
- **Passed Scenarios:** 10
- **Precision:** **100.0%**
- **Recall:** **100.0%**
- **F1-Score:** **100.0%**

---

## 4. Automated Backend Test Suite

Run the full pytest suite from the project root:

```bash
python -m pytest backend/tests -v
```

### Verified Test Results: **102 passed, 0 failed, 1 warning** in ~3.0s

| Test Suite File | Tests | Focus Area |
|---|---|---|
| `test_health.py` | 2 | Service health, readiness, and subsystem self-checks |
| `test_schema.py` | 5 | Universal Event Schema validation, port bounds, immutability |
| `test_detection.py` | 3 | Deterministic format and vendor identification heuristics |
| `test_parsers.py` | 8 | Cisco, Fortinet, Palo Alto, CEF, LEEF, JSON, CSV, and XML with XXE defense |
| `test_normalization.py` | 3 | Field alias mapping, timestamp normalization, custom fields preservation |
| `test_persistence.py` | 13 | Verbatim raw storage, SHA-256 hashing, foreign key linkages, constraints |
| `test_pipeline.py` | 3 | End-to-end ingestion pipeline, error handling, batch execution metrics |
| `test_ingest_api.py` | 3 | Format detection endpoint, single and batch REST ingestion |
| `test_onboarding.py` | 8 | Structure analyzer, type inference, field mapper, simulation, profile CRUD |
| `test_export.py` | 3 | Snappy Parquet writer, chunked export queries, REST export API |
| `test_security_analytics.py`| 7 | Source health, coverage gaps, baseline deviation engine, correlation |
| `test_supervisory_intelligence.py`| 10 | 8 capability dimensions, peer benchmarking, execution gaps, evidence chain |
| `test_syslog_udp.py` | 3 | UDP datagram reception, lifecycle, packet size limits |
| `test_syslog_tcp.py` | 4 | TCP newline framing, RFC 6587 octet-counted framing, connection limits |
| `test_syslog_tls.py` | 1 | Encrypted TLS 1.2+ listener and client transport |
| `test_syslog_queue.py` | 1 | Bounded queue backpressure protection and drop handling |
| `test_syslog_api.py` | 2 | Syslog manager status querying and metrics reset |
| `test_syslog_integration.py`| 1 | End-to-end live Syslog to database pipeline integration |
| `test_phase8_demo_validation.py`| 4 | Synthetic demo dataset generation, validation engine, demo lifecycle |
| `test_seed.py` | 1 | Database seed verification |

---

## 5. Frontend Production Build Verification

Verify that the type-safe React / Vite frontend compiles cleanly:

```bash
cd frontend
npm.cmd run build
```

### Verified Build Output
- **TypeScript Typecheck:** 0 errors
- **Vite Production Bundler:** Built in ~5.7s with 0 errors and 0 warnings
- **Static Artifacts:** Bundled into `frontend/dist/` (`index.html`, CSS, JavaScript)

---

## 6. High-Capacity Performance Benchmarks

To execute the offline high-volume performance benchmark utility:

```bash
python backend/app/utils/performance_benchmark.py
```

### Benchmark Results (Standard x86_64 Local CPU)

| Metric | 1,000 Events | 10,000 Events | 50,000 Events | 100,000 Events |
|---|---|---|---|---|
| **Raw Ingestion + SHA-256** | 1,199,904 ev/s | 1,464,043 ev/s | 1,198,808 ev/s | 1,354,059 ev/s |
| **Isolation Forest Anomaly**| 8,186 ev/s | 39,388 ev/s | 43,875 ev/s | 33,092 ev/s |
| **Alert Prioritization** | 152,263 ev/s | 67,792 ev/s | 199,657 ev/s | 197,547 ev/s |
| **8-Capability Scan Latency**| 0.069 ms | 0.081 ms | 0.053 ms | 0.061 ms |

---

## 7. Interactive Demonstration Workspace (UI Walkthrough)

For live evaluation through the web interface:
1. Open `http://localhost:5173/demo` in your browser.
2. Click **Start Demonstration** to trigger the 9-step guided workflow:
   - **Step 1:** Reset isolated evaluation tables.
   - **Step 2:** Generate multi-CSE synthetic telemetry (250+ events).
   - **Step 3:** Ingest & normalize into UES with SHA-256 hashes.
   - **Step 4:** Execute supervisory scan across 5 entities.
   - **Step 5:** Evaluate Scenarios A through J.
   - **Step 6:** Inspect Data Quality Summary (No Evidence vs Evidence of Absence vs Insufficient Data).
   - **Step 7:** Drill down into Scenarios A through J cards.
   - **Step 8:** Explore Events Explorer (`/events`) and click **Inspect** to audit the cryptographic SHA-256 raw event verification.
   - **Step 9:** Review Supervisory Assessment (`/supervisory`) for multi-entity governance.

---

## 8. Limitations & Boundary Disclaimers

1. **Synthetic Data Disclosure:** All demonstration logs and evaluation scenarios utilize strictly synthetic datasets labeled `DEMONSTRATION DATA`. No classified or production telemetry is contained within the repository.
2. **Supervisory Role:** Analytical indicators are designed for human supervisory triage and governance. The system does not claim autonomous incident adjudication without expert human review.
3. **Hardware Storage:** When executing Docker Compose on host machines, ensure at least 2 GB of free disk space is available for container image layers.

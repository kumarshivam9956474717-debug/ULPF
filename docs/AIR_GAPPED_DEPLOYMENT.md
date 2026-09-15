# OmniLogix Air-Gapped Sovereign Deployment Specification
**Universal Log Pre-processing Framework (ULPF) — SIH26156**  
**Document Version:** 1.1.0  
**Classification:** Restricted / Air-Gapped Sovereign Enclave Operations  

---

## 1. Overview & Enclave Threat Model

Modern national security enclaves, defense command centers, and critical supervised entities (CSEs) mandate **zero outbound internet egress**. In these sovereign networks:
- No DNS resolution to public root servers is available.
- No public CDNs, package repositories (PyPI, npm), or external SaaS APIs are reachable.
- Outbound network traffic is intercepted by hardware perimeter diode firewalls.
- Any software attempting unauthorized external egress triggers immediate security alerts.

OmniLogix is engineered to deploy and operate natively inside these isolated enclaves with zero external internet dependencies.

---

## 2. Air-Gap Architecture & Egress Defense Controls

```
                                 [AIR-GAPPED SOVEREIGN NETWORK ENCLAVE]
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                        │
 │  ┌──────────────────────┐         Syslog UDP:1514 / TCP:1514 / TLS:16514               │
 │  │ Perimeter Gateways   │ ──────────────────────────────────────┐                      │
 │  │ Cisco, PAN-OS, Forti │                                       │                      │
 │  └──────────────────────┘                                       ▼                      │
 │                                                   ┌────────────────────────────┐       │
 │  ┌──────────────────────┐   HTTP Ingest:8000      │   OmniLogix Core Engine    │       │
 │  │ Internal Host Logs   │ ──────────────────────► │   (AIR_GAPPED_MODE=True)   │       │
 │  └──────────────────────┘                         │   - Ingestion Daemon       │       │
 │                                                   │   - Modular Parsers        │       │
 │  ┌──────────────────────┐                         │   - UES Normalization      │       │
 │  │ Sovereign Operator   │   Browser HTTP:5173     │   - Scikit-learn ML        │       │
 │  │ SOC Workstation      │ ◄─────────────────────► │   - Parquet Data Lake Ex.  │       │
 │  │ (Local Fonts Bundled)│                         └─────────────┬──────────────┘       │
 │  └──────────────────────┘                                       │                      │
 │                                                                 ▼                      │
 │                                                   ┌────────────────────────────┐       │
 │                                                   │ Local Postgres / SQLite DB │       │
 │                                                   │ (Local Storage Volume)     │       │
 │                                                   │ - raw_events (Immutable)   │       │
 │                                                   │ - normalized_events        │       │
 │                                                   └────────────────────────────┘       │
 │                                                                                        │
 └────────────────────────────────────────────────────────────────────────────────────────┘
                                 X  NO OUTBOUND INTERNET ACCESS  X
```

### Defense Layers Implemented:
1. **Application-Level Socket Interception (`backend/app/core/airgap.py`)**:
   When `AIR_GAPPED_MODE=True`, OmniLogix installs a custom socket-level guard intercepting Python `socket.socket.connect()`.
   - **Allowed**: `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, `ulpf-db`, `ulpf-backend`, Docker bridge subnets (`172.16.0.0/12`), private LAN subnets (`10.0.0.0/8`, `192.168.0.0/16`).
   - **Blocked**: Any public Internet IP (e.g. `8.8.8.8`, `1.1.1.1`) or external domain (`api.openai.com`, `huggingface.co`). Any attempt immediately raises `PermissionError: [AIR-GAP ENCLAVE VIOLATION]`.
2. **Zero Outbound HTTP Clients**:
   The backend source code imports zero outbound HTTP client libraries (`requests`, `httpx`, `urllib`, `aiohttp`) in operational code paths.
3. **Local Font Bundling**:
   All UI typography (`Inter` and `JetBrains Mono`) is packaged locally into the production build bundle using `@fontsource/inter` and `@fontsource/jetbrains-mono`. The browser issues zero outbound requests to `fonts.googleapis.com` or `fonts.gstatic.com`.
4. **Local Machine Learning**:
   The Anomaly Engine utilizes Scikit-learn's `IsolationForest` running entirely on host CPU memory without fetching remote pre-trained weights or contacting cloud endpoints.

---

## 3. Offline Startup & Runtime Integrity

OmniLogix does **NOT** download any packages, dependencies, or models at runtime.

| Lifecycle Phase | Internet Allowed? | Action Performed |
|---|---|---|
| **Build Phase** (Air-Gap Staging) | YES | `docker build` installs Python wheels and npm dependencies into the container image. |
| **Transport Phase** | NO | Images saved as tarballs (`docker save omnilogix_backend:latest > backend.tar`) and transferred via physical media (USB/Optical diode). |
| **Runtime Phase** (Sovereign Enclave) | **STRICTLY NO** | `docker run` or `docker-compose up` executes with `--network` isolated or internal bridge only. Zero `pip install`, `npm install`, `curl`, or `wget` at startup. |

---

## 4. Configuration Reference

Air-gap behavior is controlled via environment variables in `backend/app/core/config.py` or `.env`:

```ini
# Enforce air-gapped sovereign isolation
AIR_GAPPED_MODE=True
ALLOW_EXTERNAL_CALLS=False

# Local Database Configuration (PostgreSQL container or SQLite fallback)
DATABASE_URL=postgresql://ulpf_admin:ulpf_dev_password@ulpf-db:5432/ulpf_db

# Local Syslog Ingestion Listeners (Inbound only)
SYSLOG_ENABLED=True
SYSLOG_UDP_HOST=0.0.0.0
SYSLOG_UDP_PORT=1514
SYSLOG_TCP_HOST=0.0.0.0
SYSLOG_TCP_PORT=1514
SYSLOG_TLS_HOST=0.0.0.0
SYSLOG_TLS_PORT=16514
```

---

## 5. Deployment Procedure in an Air-Gapped Network

### Step 1: Pre-Package Container Images (Outside Enclave)
On a connected build machine:
```bash
git clone https://github.com/kumarshivam9956474717-debug/ULPF.git
cd ULPF

# Build both container images
docker-compose build

# Export images to tar archive
docker save -o omnilogix_enclave_bundle.tar \
  ulpf-backend:latest \
  ulpf-frontend:latest \
  postgres:16-alpine
```

### Step 2: Transfer to Sovereign Environment
Transfer `omnilogix_enclave_bundle.tar` and `docker-compose.yml` via approved secure physical media through data diode sanitization.

### Step 3: Load and Run (Inside Air-Gapped Enclave)
```bash
# Load images into air-gapped host Docker daemon
docker load -i omnilogix_enclave_bundle.tar

# Verify no external internet route
ping -c 1 8.8.8.8 || echo "Confirmed: Zero Internet Egress"

# Launch sovereign stack
docker-compose up -d
```

---

## 6. Verification Procedure

Run the automated air-gap compliance validation utility:
```bash
python tools/test_airgap.py
```
Expected Output:
```text
======================================================================
  RESULTS: 8/8 CHECKS PASSED
======================================================================
>>> SUCCESS: OmniLogix is verified 100% AIR-GAP COMPLIANT. <<<
```

Or run via pytest:
```bash
pytest backend/tests/test_airgap.py -v
```

---

## 7. Known Limitations & Enclave Notes

1. **Self-Signed Certificates for TLS Syslog**:
   In high-security enclaves using RFC 5425 Syslog over TLS (port 16514), replace default test certificates with the enclave root CA certificates by mounting them into `/app/certs/` in the backend container.
2. **Database Engine**:
   If the PostgreSQL container is stopped or unavailable, OmniLogix automatically falls back to an embedded SQLite database (`demo.db`) inside the container filesystem, ensuring zero downtime.

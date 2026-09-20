# OmniLogix Air-Gapped Deployment & Offline Image Transfer Guide
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH 2026 Problem Statement:** SIH26156 (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Specification:** Air-Gapped Network Deployment & Offline Transfer Guide  
**Verification Level:** `VERIFIED` (Runtime & Static Assets) / `CONFIGURED` (Offline Image Transfer)  

---

## 1. Air-Gapped Architecture & Design Principles

In high-security perimeter environments (such as national defense networks, intelligence organizations, critical infrastructure, and NTRO installations), systems must operate in complete isolation from the public internet.

OmniLogix guarantees 100% offline functionality across all layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Strict Air-Gapped Perimeter Boundary                 │
│                                                                        │
│  [Syslog Devices] ──UDP/TCP/TLS──► [OmniLogix Ingestion Engine]        │
│                                                   │                    │
│                                            [ULPF Pipeline]             │
│                                                   │                    │
│  [Operator Browser] ──Local HTTP──► [Local NGINX + Bundled Assets]     │
│                                                   │                    │
│                                      [Internal PostgreSQL & Parquet]   │
│                                                                        │
│  [Outbound Internet Gateway: BLOCKED / NON-EXISTENT]                  │
└────────────────────────────────────────────────────────────────────────┘
```

### 100% Offline Operational Guarantees
- **No External CDNs:** All stylesheets, scripts, and media are served directly from container storage.
- **No Google Fonts:** Typography (`Inter`, `JetBrains Mono`) is pre-compiled into local `.woff2` font files.
- **No Cloud Identity Providers:** Authentication utilizes in-memory Bcrypt password hashing and HMAC-SHA256 JWT tokens. No OAuth, Firebase, or external STS servers are required.
- **No External Telemetry:** Zero phone-home beacons, tracking scripts, or analytics SDKs exist.
- **No Cloud Storage Runtime Requirement:** All logs, Parquet files, and relational events persist to local storage volumes.

---

## 2. Air-Gapped Verification Matrix

| Pipeline Stage | External Dependency Status | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Container Startup** | None (Local Docker Engine) | `docker compose up -d` with host network isolated | `VERIFIED` |
| **Frontend Serving** | None (All JS/CSS/Fonts bundled) | Static asset scan for URLs + offline browser execution | `VERIFIED` |
| **User Authentication** | None (Local Bcrypt + JWT HS256) | Automated test suite & `tools/validate_deployment.py` | `VERIFIED` |
| **Syslog Ingestion** | None (Local UDP/TCP/TLS sockets) | Syslog integration test suite | `VERIFIED` |
| **Format Detection** | None (Local regex + tokenization) | Universal parser suite (151 unit tests) | `VERIFIED` |
| **Normalization** | None (Local ECS/CIM schema models)| JSON schema validation tests | `VERIFIED` |
| **Forensic Hashing** | None (Local hashlib SHA-256) | Deterministic cryptographic integrity tests | `VERIFIED` |
| **Persistence** | None (Local PostgreSQL + SQLite fallback) | PostgreSQL persistent volume tests | `VERIFIED` |
| **Anomaly Analytics** | None (Local Scikit-learn IsolationForest)| Offline machine learning pipeline tests | `VERIFIED` |
| **Parquet Export** | None (Local PyArrow / Snappy) | Parquet columnar directory validation tests | `VERIFIED` |

---

## 3. Offline Image Transfer Workflow (Air-Gap Staging)

For secure facilities without internet access, Docker images are built once on a connected build machine, exported to physical media, and loaded onto the target host:

### Phase A: On the Connected Build Machine
```bash
# 1. Clone the repository and build the container images locally
git clone https://github.com/your-org/omnilogix.git
cd omnilogix

docker compose build

# 2. Package container images into a compressed archive
docker save \
  postgres:16-alpine \
  ulpf_backend:latest \
  ulpf_frontend:latest \
  | gzip > omnilogix_airgap_images.tar.gz

# 3. Compute SHA-256 checksum for media integrity verification
sha256sum omnilogix_airgap_images.tar.gz > omnilogix_airgap_images.tar.gz.sha256
```

### Phase B: Physical Transfer
Transfer the archive and checksum via approved optical media (CD/DVD-R) or write-blocked USB drive to the target air-gapped machine.

### Phase C: On the Target Air-Gapped Host
```bash
# 1. Verify transfer integrity
sha256sum -c omnilogix_airgap_images.tar.gz.sha256

# 2. Load container images into the local Docker daemon
docker load < omnilogix_airgap_images.tar.gz

# 3. Configure the offline environment file
cp .env.example .env

# 4. Start the stack in offline mode
docker compose up -d

# 5. Verify service health
docker compose ps
curl -f http://localhost:8000/api/v1/health
```

---

## 4. Active Egress Control (Defense in Depth)

In addition to removing all external references, OmniLogix backend includes an automated air-gap egress interceptor (`app.core.airgap`) that traps and denies unauthorized network socket connections when `AIR_GAPPED_MODE=True`:

```python
# Enforced during FastAPI startup lifecycle
if settings.AIR_GAPPED_MODE:
    install_airgap_guard()  # Blocks any socket connection outside loopback / docker subnet
```

This guarantees that even if a developer inadvertently imports a library that attempts an outbound telemetry call, the connection is instantly rejected at the transport layer.

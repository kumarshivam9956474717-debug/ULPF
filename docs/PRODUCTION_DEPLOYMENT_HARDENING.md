# OmniLogix Production Deployment Hardening Report
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH 2026 Problem Statement:** SIH26156 (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Specification:** Production Deployment, Docker & High-Availability Hardening  
**Verification Level:** `VERIFIED` (Single-Node Docker Stack) / `ARCHITECTURAL` (Distributed HA)  

---

## 1. Deployment Architecture

OmniLogix is packaged as a three-tier, air-gapped, containerized application stack orchestrated via Docker Compose:

```
                  Operator Browser / Analyst Workstation
                                    │
                                    │ HTTP / Port 5173
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                Tier 1: Frontend Proxy                   │
       │                   (Alpine / NGINX)                      │
       │  • Bundled React 18 SPA (Local fonts & static JS/CSS)   │
       │  • Reverse-proxies /api/ to internal backend service    │
       └────────────────────────────┬────────────────────────────┘
                                    │
                         (Internal Docker Network)
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │             Tier 2: Backend Core Processing             │
       │              (Python 3.12-slim / FastAPI)               │
       │  • Non-root process (UID 10001: omnilogix)              │
       │  • Syslog listeners: UDP 1514, TCP 1514, TLS 16514      │
       │  • Universal Parser, Anomaly Engine, SIEM Exporters     │
       │  • Decoupled Async Batch Persistence Queue              │
       └────────────────────────────┬────────────────────────────┘
                                    │
                         (Internal Docker Network)
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                Tier 3: Persistence Layer                │
       │                  (PostgreSQL 16-Alpine)                 │
       │  • Named volume: postgres_data                          │
       │  • Bound to host loopback: 127.0.0.1:5432               │
       │  • Automatic SQLite resilient fallback engine           │
       └─────────────────────────────────────────────────────────┘
```

---

## 2. Docker Architecture

The stack defines three synchronized container services in `docker-compose.yml`:
1. **`ulpf-db`**: PostgreSQL 16 Alpine container with an active `pg_isready` healthcheck probe.
2. **`ulpf-backend`**: Builds from `backend/Dockerfile`. Uses `depends_on: { ulpf-db: { condition: service_healthy } }` to ensure zero startup race conditions.
3. **`ulpf-frontend`**: Builds from `frontend/Dockerfile`. Uses `depends_on: { ulpf-backend: { condition: service_healthy } }` to ensure the API is fully ready before serving client traffic.

---

## 3. Container Security

- **Non-Root Execution:** The backend container establishes an unprivileged system user (`omnilogix`, UID 10001) with restricted permissions to `/app/data`.
- **Minimal Base Images:** Built using `python:3.12-slim` and `nginx:alpine` to eliminate build compilers and reduce vulnerability surfaces.
- **Layer Optimization:** Build dependencies (`build-essential`, `libpq-dev`) are cleaned up in the same RUN layer (`rm -rf /var/lib/apt/lists/*`).
- **Deterministic Dependencies:** Frontend uses `npm ci` with `package-lock.json`; backend uses pinned `requirements.txt`.

---

## 4. PostgreSQL Hardening

- **Host Isolation:** Published port is restricted to `127.0.0.1:${POSTGRES_PORT:-5432}:5432`, blocking external subnet access.
- **Dynamic Credentials:** Configured via `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` environment variables.
- **Resilient Engine:** `app.core.database.create_resilient_engine` tests connections using `SELECT 1` with connection pooling (`DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=30`). If PostgreSQL is stopped, the engine gracefully activates local SQLite fallback mode (`sqlite:///./demo.db`).

---

## 5. Environment Configuration

All system options are driven by `.env` with comprehensive placeholders in `.env.example`:
- **Core:** `ENVIRONMENT`, `DEBUG`, `AIR_GAPPED_MODE`
- **Security:** `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Database:** `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_POOL_SIZE`
- **Persistence Queue:** `PERSISTENCE_MODE`, `PERSISTENCE_BATCH_SIZE`, `PERSISTENCE_FLUSH_INTERVAL_MS`
- **Syslog Transports:** `SYSLOG_ENABLED`, `SYSLOG_UDP_PORT`, `SYSLOG_TCP_PORT`, `SYSLOG_TLS_PORT`

---

## 6. Secret Management

- Zero production passwords or JWT secrets are hardcoded in the codebase.
- Passwords use salted Bcrypt hashing (12 rounds) stored in `users.hashed_password`.
- Admin bootstrap credentials are provided via environment variables at container startup or created interactively via `tools/create_admin.py`.

---

## 7. Network Security

- Internal communication operates across the Docker bridge `ulpf-network`.
- Database access is restricted to the internal network and local loopback.
- CORS is locked to approved client origins (`ALLOWED_ORIGINS`).
- Security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`) are automatically injected into all HTTP responses.

---

## 8. Health Checks & Observability

- **Database Probe:** Docker inspects `pg_isready -U ulpf_admin -d ulpf_db` every 5s.
- **Backend Probe:** Evaluates `GET /api/v1/health` every 10s. The endpoint executes an active database query (`SELECT 1`) and checks the `global_persistence_queue.is_running` status. If degraded, it returns HTTP 503.
- **Frontend Probe:** Evaluates `wget -q -O /dev/null http://localhost:80/` every 10s.

---

## 9. Persistent Storage

- **PostgreSQL Data:** Stored in the named Docker volume `postgres_data` mapped to `/var/lib/postgresql/data`. Data survives `docker compose down` and container restarts.
- **Columnar Exports (Parquet):** Written to `./data/processed` via a persistent host bind-mount (`./data:/app/data`), ensuring immediate availability for external analytics tools.

---

## 10. Restart Recovery

The system was audited against component restarts:
1. **Database Failure / Restart:**
   - When PostgreSQL recovers, SQLAlchemy connection pools re-establish connectivity seamlessly via `pool_pre_ping=True`.
2. **Backend Restart:**
   - In-flight database tables and stored logs persist.
   - Frontend automatically reconnects as soon as the backend healthcheck returns `200 OK`.
3. **Frontend Restart:**
   - NGINX re-reads static assets and proxies API calls without disrupting backend ingestion.

---

## 11. Air-Gapped Deployment

- 100% offline functionality verified.
- Fonts are bundled directly into the distribution as local `.woff2` files.
- Zero CDNs, Google Fonts, or cloud authentication providers are referenced.
- Outbound network calls are blocked by default via `AIR_GAPPED_MODE=True`.

---

## 12. Offline Docker Image Workflow

For air-gapped environments without registry access:
```bash
# On build machine:
docker compose build
docker save postgres:16-alpine ulpf_backend:latest ulpf_frontend:latest | gzip > omnilogix_images.tar.gz

# On air-gapped machine:
docker load < omnilogix_images.tar.gz
docker compose up -d
```

---

## 13. Platform Independence

OmniLogix operates identically on:
- **Windows** (via Docker Desktop / WSL2)
- **Linux** (Ubuntu, RHEL, Rocky Linux, Debian via native Docker Engine)
- **macOS** (via Docker Desktop / Colima)

No hardcoded platform paths exist. Path resolution uses standard Python `pathlib.Path` and POSIX container conventions.

---

## 14. Scalability

- Ingestion and database writes are decoupled via `global_persistence_queue`.
- Batch insertion reduces per-event write latency from 7.78ms to 0.10ms (a 98.7% reduction).
- Worker thread concurrency and queue buffer limits are dynamically configurable.

---

## 15. High Availability Status

| Layer | Status | Implementation Details |
| :--- | :--- | :--- |
| **Ingestion Worker Pool** | `VERIFIED` | Multi-worker asyncio pool with decoupled queue backpressure. |
| **Single-Node Container Stack**| `VERIFIED` | Docker Compose orchestration with automated health recovery. |
| **Multi-Node Database Cluster**| `ARCHITECTURAL` | Documented Patroni / pgpool-II topology in `SCALABLE_DEPLOYMENT_ARCHITECTURE.md`. |
| **Distributed Broker (Kafka)** | `ARCHITECTURAL` | StreamingSink abstraction interface implemented; cluster topology documented. |
| **Zero-Downtime Rolling Update**| `ARCHITECTURAL` | Supported via Kubernetes / Swarm rolling deployment specifications. |

---

## 16. Judge Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/omnilogix.git
cd omnilogix

# 2. Configure environment
cp .env.example .env

# 3. Start the stack
docker compose up -d

# 4. Verify deployment health
python tools/validate_deployment.py
```

Access the Web UI at: `http://localhost:5173`  
Access API Documentation at: `http://localhost:8000/docs`

---

## 17. Verified Tests

- **Backend Pytest Baseline:** **151/151 passed (100% green)** in 29.50s.
- **Frontend Production Build:** **Built successfully** via `npm run build` in 6.27s.
- **Deployment Validation Suite:** **7/7 checks passed** via `tools/validate_deployment.py`.
- **Docker Compose Syntax:** Validated via `docker compose config` (Exit code: 0).

---

## 18. Known Limitations

1. **Clustering:** Current out-of-the-box Compose stack runs as a single-node multi-container deployment. High-availability multi-node clustering (Patroni/Kafka) is documented as an enterprise architectural blueprint.
2. **Data Deletion on `-v`:** Running `docker compose down -v` explicitly destroys the database volume. This is standard Docker behavior and documented in setup instructions.

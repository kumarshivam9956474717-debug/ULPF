# OmniLogix Deployment Audit
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH 2026 Problem Statement:** SIH26156 (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Evaluation Phase:** Step 6 — Production Deployment, Docker & High-Availability Hardening  
**Audit Timestamp:** September 2026

---

## 1. Executive Summary

This deployment audit evaluates the containerized packaging, service lifecycle, security posture, network isolation, and runtime independence of OmniLogix ULPF. The stack is containerized using Docker Compose and Dockerfiles designed to guarantee deterministic, reproducible, and strictly air-gapped execution without requiring manual source-code modifications.

### Deployment Capability Classification
| Capability | Classification | Technical Evidence |
| :--- | :--- | :--- |
| **Containerized Deployment** | `VERIFIED` | Validated via `docker compose config`, Dockerfiles, multi-stage builds. |
| **Air-Gapped Runtime** | `VERIFIED` | Zero outbound external runtime dependencies, local font bundling, egress blocking. |
| **PostgreSQL Persistence** | `VERIFIED` | Named volume `postgres_data`, restart recovery, automated fallback engine. |
| **Non-Root Container Execution** | `VERIFIED` | Unprivileged user `omnilogix` (UID 10001:GID 10001) in `Dockerfile`. |
| **Active Health Probing** | `VERIFIED` | `/api/v1/health` probes active DB ping (`SELECT 1`) & queue state, returns 503 if degraded. |
| **High Availability Clustering** | `ARCHITECTURAL` | Multi-worker persistence queue implemented; multi-node DB/broker clustering documented in `docs/SCALABLE_DEPLOYMENT_ARCHITECTURE.md`. |

---

## 2. Container Topology & Startup Order

```
[Host System / Evaluator Client]
        │
        │ HTTP :5173 (or :80)
        ▼
┌───────────────────────────────────────────────────────────┐
│                      ulpf-frontend                        │
│                   (NGINX Alpine SPA)                      │
│   Serves bundled static assets (JS, CSS, WOFF2 Fonts)     │
│   Reverse proxies /api/ requests to ulpf-backend:8000     │
└─────────────────────────────┬─────────────────────────────┘
                              │
               (ulpf-network Docker Bridge)
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│                      ulpf-backend                         │
│               (FastAPI / Python 3.12-slim)                │
│   Non-root user (omnilogix: 10001)                        │
│   Syslog Listeners: UDP 1514, TCP 1514, TLS 16514        │
│   Decoupled Batch Persistence & Data Lake Exporters       │
└─────────────────────────────┬─────────────────────────────┘
                              │
               (ulpf-network Docker Bridge)
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│                        ulpf-db                            │
│                 (PostgreSQL 16-Alpine)                    │
│   Persistent Volume: postgres_data -> /var/lib/postgresql │
│   Healthcheck: pg_isready                                 │
│   Host Bind: 127.0.0.1:5432 (Internal to host/container)  │
└───────────────────────────────────────────────────────────┘
```

### Startup Dependency Chain
1. **`ulpf-db` (PostgreSQL 16 Alpine)** starts first.
   - Initialized with `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
   - Healthcheck: `pg_isready -U ${POSTGRES_USER:-ulpf_admin} -d ${POSTGRES_DB:-ulpf_db}` runs every 5s.
2. **`ulpf-backend` (FastAPI / Uvicorn)**:
   - Configured with `depends_on.ulpf-db.condition: service_healthy`.
   - Executes database schema initialization (`init_db()`), bootstrap admin verification (`init_admin_bootstrap()`), and starts Syslog listeners & persistence queue.
   - Healthcheck: Probes `http://localhost:8000/api/v1/health` every 10s.
3. **`ulpf-frontend` (NGINX Alpine)**:
   - Configured with `depends_on.ulpf-backend.condition: service_healthy`.
   - Reverse-proxies all `/api/` traffic to `http://ulpf-backend:8000/api/`.

---

## 3. Configuration & Parameter Audit

| Parameter | Default Container Value | Source / Scope | Classification |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Container env | Hardened default |
| `DEBUG` | `False` | Container env | Safe production setting |
| `AIR_GAPPED_MODE` | `True` | Container env & `config.py` | Strict air-gap egress enforcement |
| `DATABASE_URL` | `postgresql://ulpf_admin:...@ulpf-db:5432/ulpf_db` | Container env | Internal bridge DNS resolution |
| `JWT_SECRET_KEY` | Overridden via `.env` / env var | Container env | Cryptographic token signing |
| `PERSISTENCE_MODE` | `batch` | Container env | High-throughput decoupled persistence |
| `PERSISTENCE_BATCH_SIZE` | `500` | Container env | Batch transaction sizing |
| `PERSISTENCE_FLUSH_INTERVAL_MS`| `100` | Container env | Maximum flush latency buffer |
| `PERSISTENCE_QUEUE_MAX_SIZE` | `50000` | Container env | In-memory backpressure boundary |
| `DB_POOL_SIZE` | `20` | Container env | SQLAlchemy connection pool |
| `DB_MAX_OVERFLOW` | `30` | Container env | Burst connection limit |
| `SYSLOG_UDP_PORT` | `1514` | Container env & compose | Unprivileged network listener |
| `SYSLOG_TCP_PORT` | `1514` | Container env & compose | Unprivileged network listener |
| `SYSLOG_TLS_PORT` | `16514` | Container env & compose | Secure encrypted network listener |

---

## 4. Volume & Data Retention Audit

| Volume / Bind Path | Target Container Path | Content Description | Destruction Risk |
| :--- | :--- | :--- | :--- |
| `postgres_data` (Volume) | `/var/lib/postgresql/data` | Relational tables, raw log records, audit trails, user RBAC hashes. | **Survives `docker compose down`.** Destroyed only if `-v` is explicitly passed. |
| `./data` (Host Bind Mount) | `/app/data` | Parquet columnar files, raw captures, exported compliance bundles. | **Survives container recreation and `docker compose down -v`.** |

---

## 5. Security & Isolation Audit

1. **Database Exposure:**
   - PostgreSQL port `5432` is bound to `127.0.0.1:${POSTGRES_PORT:-5432}:5432`.
   - External networks cannot access PostgreSQL directly; only the local host and containers on `ulpf-network` can connect.
2. **Container Privilege:**
   - The backend runs as unprivileged user `omnilogix` (UID 10001).
   - Root privilege is eliminated inside the application runtime.
3. **Frontend Independence:**
   - All web fonts (`Inter`, `JetBrains Mono`) are compiled locally as `.woff2` assets.
   - Zero CDN references exist in index.html, CSS, or TypeScript bundles.
4. **Secret Hygiene:**
   - `.env.example` contains only non-sensitive placeholders.
   - No production secrets or credentials are hardcoded into Git.

---

## 6. Audit Conclusion
The OmniLogix deployment architecture complies fully with container security standards, provides reliable healthchecks and restart recovery, enforces air-gapped runtime constraints, and requires minimum manual configuration for evaluators.

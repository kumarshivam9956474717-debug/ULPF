# Universal Log Pre-processing Framework (ULPF)
## Deployment & Operations Guide

**Project:** Universal Log Pre-processing Framework (ULPF)  
**Smart India Hackathon 2026** | **Problem Statement:** `SIH26156`  
**Organization:** National Technical Research Organisation (NTRO)  
**Theme:** Blockchain & Cybersecurity  
**Deployment Profile:** Air-Gapped / On-Premises Evaluation  

---

## 1. Prerequisites

### Option A: Docker Compose Deployment (Recommended for Evaluators)
- **Operating System:** Linux, macOS, or Windows 10/11 (WSL2)
- **Tools Required:**
  - Git
  - Docker Engine (v24.0+) & Docker Compose (v2.20+)
  - *Zero local installation of Python, Node.js, or PostgreSQL is required on the host system.*

### Option B: Local Native Deployment (For Development & Direct Host Execution)
- **Python:** Python 3.12+ (tested on Python 3.12, 3.13, 3.14)
- **Node.js:** Node.js 20+ and npm
- **Database:** PostgreSQL 16 (optional; the framework automatically falls back to an isolated SQLite engine `sqlite:///./demo.db` if PostgreSQL is unavailable)
- **C/C++ Build Tools:** Standard build-essential or MSVC tools (for compiling native Python extensions like `psycopg2`)

---

## 2. Port Matrix & Network Bindings

| Service | Container Port | Host Port | Protocol | Purpose |
|---|---|---|---|---|
| **Frontend UI** | `80` | `5173` | TCP | Single-page application & Nginx reverse proxy |
| **Backend REST API** | `8000` | `8000` | TCP | FastAPI application & OpenAPI Swagger UI (`/docs`) |
| **Syslog UDP** | `1514` | `1514` | UDP | High-speed RFC 3164 / RFC 5424 datagram listener |
| **Syslog TCP** | `1514` | `1514` | TCP | Delimited and octet-counted streaming listener |
| **Syslog TLS** | `16514` | `16514` | TCP | Encrypted syslog listener (TLS 1.2+) |
| **PostgreSQL Database** | `5432` | `5432` | TCP | Relational metadata and telemetry storage |

---

## 3. Docker Compose Deployment (Quick Start)

### Step 1: Clone Repository
```bash
git clone <repository_url>
cd ULPF
```

### Step 2: Environment Configuration (Optional)
The system includes safe defaults out of the box. To customize ports or settings:
```bash
cp .env.example .env
```

### Step 3: Launch Multi-Tier Application Stack
```bash
# Build images and start services in detached mode
docker compose up --build -d
```

### Step 4: Verify Container Health
```bash
docker compose ps
```
All containers (`ulpf_postgres`, `ulpf_backend`, `ulpf_frontend`) will transition to `healthy` state once internal health checks pass.

### Step 5: Access Interfaces
- **SIH Demonstration Workspace:** `http://localhost:5173/demo`
- **Dashboard & Overview:** `http://localhost:5173`
- **Interactive API Documentation (Swagger):** `http://localhost:8000/docs` *(or `http://localhost:5173/docs`)*
- **Subsystem Health Check:** `http://localhost:8000/api/v1/health`

### Stopping & Teardown
```bash
# Graceful stop preserving database volumes
docker compose down

# Stop and wipe persistent database volumes (clean re-initialization)
docker compose down -v
```

---

## 4. Local Native Deployment (Manual Step-by-Step)

### Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Start FastAPI application server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Setup
In a second terminal:
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 5. Environment Configuration Parameters

Configuration is loaded from environment variables or a `.env` file based on `.env.example`:

| Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Deployment mode (`development`, `production`, `test`) |
| `DEBUG` | `False` | Enables detailed debug logging and SQL query echoes |
| `DATABASE_URL` | `postgresql://ulpf_admin:ulpf_dev_password@ulpf-db:5432/ulpf_db` | Database connection string (PostgreSQL or SQLite) |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173` | Comma-separated CORS allowed origins |
| `AIR_GAPPED_MODE` | `True` | Enforces strict air-gapped operational constraints |
| `SYSLOG_ENABLED` | `True` | Master toggle for background Syslog network listeners |
| `SYSLOG_UDP_PORT` | `1514` | Port for incoming UDP Syslog datagrams |
| `SYSLOG_TCP_PORT` | `1514` | Port for incoming TCP Syslog streams |
| `SYSLOG_TLS_PORT` | `16514` | Port for incoming TLS Syslog streams |
| `SYSLOG_MAX_MESSAGE_BYTES`| `65536` | Maximum allowed payload size per syslog message |
| `SYSLOG_QUEUE_MAXSIZE` | `10000` | Ingestion queue capacity before backpressure action |
| `SYSLOG_WORKERS` | `4` | Number of concurrent asynchronous worker tasks |

---

## 6. Air-Gapped & Offline Facility Deployment Notes

For deployment into classified or disconnected defense enclaves with zero WAN connectivity:
1. **Dependency Pre-packaging:**
   - Download Python wheel dependencies onto portable media using `pip download -r backend/requirements.txt -d ./wheels`.
   - In the target environment, install via `pip install --no-index --find-links=./wheels -r requirements.txt`.
2. **Docker Image Transfer:**
   - Export container images on an internet-connected staging machine:
     ```bash
     docker save -o ulpf-images.tar ulpf-ulpf-backend:latest ulpf-ulpf-frontend:latest postgres:16-alpine
     ```
   - Import on the isolated target machine:
     ```bash
     docker load -i ulpf-images.tar
     ```
3. **Synthetic Ground Truth:**
   - The repository bundles reproducible synthetic datasets under `data/synthetic/`, enabling end-to-end functionality verification without connecting to live operational feeds.

---

## 7. Troubleshooting & Operational Diagnostics

### 1. Port 8000 or 5173 Already in Use
- **Symptom:** `bind: address already in use` error when launching Docker or dev servers.
- **Resolution:** Check running processes using `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Linux) and terminate lingering development processes.

### 2. Database Connection Refused
- **Symptom:** `(psycopg2.OperationalError) connection to server at "localhost", port 5432 failed`.
- **Behavior:** ULPF automatically catches this and falls back to an isolated local SQLite database (`sqlite:///./demo.db`). All functionality remains 100% operational.
- **Resolution for PostgreSQL:** Ensure PostgreSQL is running (`docker compose ps ulpf-db`) and healthy before starting the backend.

### 3. Container Disk Space / Emergency Read-Only Filesystem
- **Symptom:** `read-only file system` error during Docker build.
- **Root Cause:** Host system drive reached 100% capacity, causing the underlying virtual disk to mount read-only.
- **Resolution:** Free up disk space on the host drive (at least 2 GB recommended) and execute `docker builder prune -f`.

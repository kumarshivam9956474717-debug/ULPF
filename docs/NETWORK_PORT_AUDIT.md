# OmniLogix Network Port & Protocol Security Audit
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH 2026 Problem Statement:** SIH26156 (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Evaluation Phase:** Step 6 — Production Deployment, Docker & High-Availability Hardening  
**Scope:** Complete Port Exposure Analysis for Containerized Stack  

---

## 1. Network Topology & Port Mapping Overview

OmniLogix minimizes host-level attack surfaces by isolating database and internal services within an unrouted bridge network (`ulpf-network`), exposing only required application ingress points.

```
       Evaluator / Operator Browser                    Network Firewalls / Endpoints
               │                                                    │
               │ HTTP                                               │ Syslog (RFC 5424/3164)
               ▼                                                    ▼
     ┌───────────────────┐                               ┌──────────────────────┐
     │   Port 5173 TCP   │                               │   Ports 1514 UDP/TCP │
     │  (Frontend NGINX) │                               │   Port 16514 TLS     │
     └─────────┬─────────┘                               └──────────┬───────────┘
               │ Internal                                           │ Direct
               ▼                                                    ▼
     ┌──────────────────────────────────────────────────────────────────────────┐
     │                       Port 8000 TCP (ulpf-backend)                       │
     └────────────────────────────────────┬─────────────────────────────────────┘
                                          │ Internal Docker Bridge only
                                          ▼
                             ┌─────────────────────────┐
                             │  Port 5432 TCP (db)     │
                             │ (127.0.0.1 host loopback)│
                             └─────────────────────────┘
```

---

## 2. Port Audit & Security Specification

| Port | Protocol | Service / Container | Scope | Default Host Bind | Purpose | Security Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **5173** | TCP | `ulpf-frontend` (NGINX) | External (Host) | `0.0.0.0:5173` | Web UI, SPA static asset distribution, reverse-proxy for `/api/`. | Production reverse proxy should terminate TLS (HTTPS). Content Security Policy (CSP) headers applied. |
| **8000** | TCP | `ulpf-backend` (FastAPI) | External (Host) | `0.0.0.0:8000` | REST API, OpenAPI docs (`/docs`), healthcheck endpoint (`/api/v1/health`). | Enforces Bearer JWT authentication and RBAC privileges across endpoints. Protected against unauthenticated tampering. |
| **1514** | UDP | `ulpf-backend` (UDPListener) | External (Network)| `0.0.0.0:1514/udp` | Ingestion of high-throughput RFC 3164/5424 Syslog datagrams from perimeter devices. | Connectionless protocol. Protected by kernel socket buffers and in-memory backpressure queues. |
| **1514** | TCP | `ulpf-backend` (TCPListener) | External (Network)| `0.0.0.0:1514/tcp` | Reliable stream-oriented Syslog ingestion with framer detection. | Max connection limit (default 100) and idle connection timeouts (default 60s) prevent slowloris/exhaustion attacks. |
| **16514**| TCP | `ulpf-backend` (TLSListener) | External (Network)| `0.0.0.0:16514/tcp`| Encrypted RFC 5425 TLS Syslog transport for untrusted network traversal. | Cryptographic confidentiality and mutual TLS (mTLS) client verification capability using local PKI certificates. |
| **5432** | TCP | `ulpf-db` (PostgreSQL) | **Internal / Loopback** | `127.0.0.1:5432` | Relational storage for raw logs, normalized entities, parsing profiles, and users. | **Strictly bound to 127.0.0.1.** Inaccessible from external host interfaces. Accessible only via Docker network `ulpf-network` or local host debugging. |

---

## 3. Host Attack Surface Minimization

1. **PostgreSQL Protection:**
   - In standard Docker configurations, publishing `5432:5432` binds to `0.0.0.0:5432`, leaving the database vulnerable to external network scans.
   - OmniLogix configures `127.0.0.1:${POSTGRES_PORT:-5432}:5432`, ensuring that only processes on `localhost` or within the private Docker bridge network can communicate with the PostgreSQL daemon.
2. **Unprivileged Syslog Listeners:**
   - Default Syslog ports `514` (UDP/TCP) and `6514` (TLS) require `root` / `CAP_NET_BIND_SERVICE` on Linux hosts.
   - OmniLogix defaults to non-privileged ports `1514` and `16514`, enabling the backend container to execute completely under unprivileged user `omnilogix` (UID 10001).
3. **CORS Isolation:**
   - Production backend restricts allowed origins to explicit origins (`ALLOWED_ORIGINS`).
   - Browser cross-origin attacks from arbitrary origins are rejected.

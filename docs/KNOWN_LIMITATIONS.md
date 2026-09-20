# OmniLogix Known Limitations & Operational Boundaries
**Universal Log Pre-Processing Framework (ULPF)**  
**SIH Problem Statement:** `SIH26156` (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Phase:** Step 7 — Final SIH Evaluation Readiness  
**Integrity Rule:** Absolute Transparency (Never convert architectural designs into implemented claims).

---

## 1. Architectural Boundaries

### A. Single-Node Stack vs. Distributed Clustering
- **Verified:** The single-node Docker Compose stack (`ulpf-db`, `ulpf-backend`, `ulpf-frontend`) is fully verified, operational, and benchmarked.
- **Architectural:** Distributed Kafka clustering, Patroni multi-node PostgreSQL replication, and HAProxy layer-4 load balancing are architecturally designed and documented in `docs/SCALABLE_DEPLOYMENT_ARCHITECTURE.md`, but not deployed as live multi-server clusters in the evaluation repository.

### B. In-Memory Persistence Queue Bounds
- The asynchronous persistence queue (`backend/app/services/persistence/queue.py`) enforces a configurable memory bound (`PERSISTENCE_QUEUE_MAX_SIZE=50000`, default).
- If database writes are suspended for extended durations and the in-memory buffer exceeds 50,000 events, subsequent events are handled according to the selected overflow policy (backpressure block or discard with logged warning). For production deployments exceeding 100,000 ev/s sustained over hours, external message brokers (Kafka) are recommended.

### C. SQLite Fallback Mode
- OmniLogix features a resilient database fallback engine (`app.core.database.create_resilient_engine`). If PostgreSQL is offline or unreachable, the engine gracefully transitions to local SQLite (`sqlite:///./demo.db`).
- While SQLite allows full standalone demonstration, zero-loss testing, and offline evaluator verification, it is single-writer constrained and not intended for high-throughput multi-gigabit perimeter production.

---

## 2. Ingestion & Format Boundaries

### A. Dynamic Format Inference on Obfuscated Streams
- The No-Code Structure Analyzer successfully tokenizes JSON, CSV, TSV, key-value (`k=v`), and standard pipe/colon delimited formats.
- Highly unstructured or free-form arbitrary natural language log streams without consistent token separators require operator assistance in the No-Code UI to define custom regex extraction patterns.

### B. Encrypted Syslog (TLS)
- TLS Syslog on port 16514 TCP is verified using local self-signed X.509 certificates. In high-assurance NTRO deployments, mutual TLS (mTLS) with organization-issued PKI certificates must be provisioned.

---

## 3. Resource & Storage Considerations

- **Memory:** Minimum recommended RAM is 4 GB (8 GB recommended for high-volume benchmarks exceeding 50,000 ev/s).
- **Disk Space:** Parquet columnar compression reduces raw log footprint by ~85-90%. However, storing raw and normalized logs concurrently in PostgreSQL requires adequate storage planning for long-term multi-year retention.

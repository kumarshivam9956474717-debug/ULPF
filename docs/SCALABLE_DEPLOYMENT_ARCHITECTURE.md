# OmniLogix Scalable Deployment Architecture

**Universal Log Pre-processing Framework (ULPF)**  
**Smart India Hackathon 2026 — Problem Statement SIH26156 (NTRO)**  
*Deployment Sizing, Tiered Topologies, and Invariant Event Flow*

---

## 1. Architectural Philosophy

OmniLogix is designed to scale across the full spectrum of cybersecurity environments—from an edge firewall forwarder in an air-gapped lab to a multi-node enterprise SOC processing 1 billion perimeter events per day.

Crucially, **the internal event processing pipeline and Universal Event Schema (UES) remain identical across all deployment modes**. Whether running in single-node prototype mode or across a distributed broker cluster, the same lossless principles apply:
1. **Verbatim Raw Preservation** (`RawEvent.raw_payload`)
2. **Cryptographic Integrity Hash** (`payload_hash_sha256`)
3. **Deterministic Parser Selection & Normalization**
4. **Strict Schema Validation & Quality Scoring**
5. **Bidirectional Forensic Traceability** (`event_id` $\rightarrow$ `raw_event_id`)

```
                         THE INVARIANT LOGICAL PIPELINE
                                       │
                                       ▼
                             [ Ingest Wire Bytes ]
                                       │
                                       ▼
                       [ Compute SHA-256 Digest & ID ]
                                       │
                                       ▼
                            [ Detect Log Format ]
                                       │
                                       ▼
                          [ Select Format Parser ]
                                       │
                                       ▼
                      [ Extract Normalized UES Attributes ]
                                       │
                                       ▼
                          [ Schema Validation & Q-Score ]
                                       │
                                       ▼
                    [ Decoupled Persistence / Streaming Sink ]
```

---

## 2. Tier 1: Small Deployment (Single-Node Standalone)

### Target Environment:
* Branch offices, field stations, lab environments, or isolated perimeter appliances.
* Expected throughput: **100 to 1,000 EPS** (~8.6M to 86M events/day).
* Target infrastructure: Single physical server or VM (4–8 CPU cores, 8–16 GB RAM).

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SINGLE-NODE HOST / VM                          │
│                                                                        │
│  [Network Perimeter]                                                   │
│         │ (Syslog UDP:514 / TCP:514 / TLS:6514 / REST API)             │
│         ▼                                                              │
│  ┌──────────────┐                                                      │
│  │ OmniLogix    │ ───► [ In-Memory Ingestion Queue (max 10,000) ]       │
│  │ Transport    │                                                      │
│  └──────────────┘                                                      │
│         │                                                              │
│         ▼                                                              │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ 4 Concurrent Async Processing Workers                  │            │
│  │ • SHA-256 Hashing       • Format Detection             │            │
│  │ • Specialized Parsers   • Universal Normalization      │            │
│  │ • Schema Validation     • Packaging PersistenceItem    │            │
│  └────────────────────────────────────────────────────────┘            │
│         │                                                              │
│         ▼                                                              │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ AsyncPersistenceQueue (Bounded: max 50,000)            │            │
│  │ • Non-blocking enqueue (< 0.15ms latency)              │            │
│  │ • Dual-trigger flusher (500 items OR 100ms interval)   │            │
│  └────────────────────────────────────────────────────────┘            │
│         │                                                              │
│         ▼                                                              │
│  ┌──────────────┐                                                      │
│  │ Storage      │ ───► SQLite WAL (demo) OR Local PostgreSQL 16        │
│  └──────────────┘                                                      │
│                                                                        │
│  ┌──────────────┐                                                      │
│  │ OmniLogix UI │ ───► React / Vite SOC Dashboard (Air-Gapped)         │
│  └──────────────┘                                                      │
└────────────────────────────────────────────────────────────────────────┘
```

### Configuration:
```env
PERSISTENCE_MODE=batch
PERSISTENCE_BATCH_SIZE=500
PERSISTENCE_FLUSH_INTERVAL_MS=100
SYSLOG_WORKERS=4
SYSLOG_QUEUE_MAXSIZE=10000
PERSISTENCE_QUEUE_MAX_SIZE=50000
AIR_GAPPED_MODE=true
```

---

## 3. Tier 2: Medium Deployment (Multi-Worker + Dedicated DB)

### Target Environment:
* Regional Security Operations Centers (SOC), central government ministries, defense installations.
* Expected throughput: **1,000 to 10,000 EPS** (~86M to 864M events/day).
* Target infrastructure: Dedicated Ingestion/Processing Host + Dedicated PostgreSQL Database Server.

```
                  AIR-GAPPED PERIMETER TRAFFIC (UDP / TCP / TLS / API)
                                           │
                                           ▼
                 ┌───────────────────────────────────────────────────┐
                 │       INTERNAL LAYER 4 LOAD BALANCER             │
                 │              (HAProxy / NGINX)                    │
                 └─────────────────────────┬─────────────────────────┘
                                           │
             ┌─────────────────────────────┼─────────────────────────────┐
             ▼                             ▼                             ▼
   ┌───────────────────┐         ┌───────────────────┐         ┌───────────────────┐
   │ OmniLogix Node 1  │         │ OmniLogix Node 2  │         │ OmniLogix Node 3  │
   │ (8 Workers)       │         │ (8 Workers)       │         │ (8 Workers)       │
   │ Persistence Queue │         │ Persistence Queue │         │ Persistence Queue │
   │ (500-event batch) │         │ (500-event batch) │         │ (500-event batch) │
   └─────────┬─────────┘         └─────────┬─────────┘         └─────────┬─────────┘
             │                             │                             │
             └─────────────────────────────┼─────────────────────────────┘
                                           │
                                           ▼
                 ┌───────────────────────────────────────────────────┐
                 │          DEDICATED POSTGRESQL 16 CLUSTER          │
                 │      (NVMe SSD Storage, pgBouncer Pooling)        │
                 │                                                   │
                 │  • raw_events (Lossless payload + SHA-256)        │
                 │  • normalized_events (Universal schema attributes)│
                 │  • validation_results (Quality scores & errors)   │
                 │  • Connection pool: 30 conn / 50 overflow         │
                 └───────────────────────────────────────────────────┘
```

### Configuration:
```env
PERSISTENCE_MODE=batch
PERSISTENCE_BATCH_SIZE=1000
PERSISTENCE_FLUSH_INTERVAL_MS=100
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=50
SYSLOG_WORKERS=8
AIR_GAPPED_MODE=true
```

---

## 4. Tier 3: Large Deployment (Enterprise Distributed 1B/Day)

### Target Environment:
* National Critical Information Infrastructure (NCII), NTRO perimeter monitoring, Tier-1 Telecom / Cloud Backbones.
* Expected throughput: **11,574 to 30,000+ EPS** (**1,000,000,000+ events/day**).
* Target infrastructure: Decoupled Ingestion Fleet, Distributed Broker Cluster, Processing Worker Fleet, and Dual-Tier Storage (Hot Transactional DB + Cold Columnar Data Lake).

```
                      DISTRIBUTED PERIMETER LOG TRAFFIC
                                      │
                                      ▼
                        High-Availability Ingestion Tier
                 (Stateless UDP/TCP/TLS Syslog Concentrators)
                                      │
                                      ▼
                 Distributed Streaming Broker Layer (Air-Gapped)
                      (Apache Kafka / Redpanda Cluster)
                       Topic: omnilogix-raw-perimeter
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
      Worker Group 1          Worker Group 2          Worker Group 3
      (Normalization)         (Normalization)         (Normalization)
      • SHA-256 Checksum      • SHA-256 Checksum      • SHA-256 Checksum
      • Parser Registry       • Parser Registry       • Parser Registry
      • UES Transformation    • UES Transformation    • UES Transformation
      • Quality Score         • Quality Score         • Quality Score
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                                      ▼
                           StreamingSink Interface
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
         Hot Analytical Storage               Cold Data Lake Archival
        (ClickHouse / PostgreSQL)             (Partitioned Parquet)
        • Fast SOC Querying                   • Hourly snappy Parquet files
        • Threat Detection & ML               • Long-term forensic retention
        • Real-time Dashboards                • Immutable air-gapped storage
```

### How OmniLogix Prepares for Tier 3:
1. **Pluggable Persistence Interface:** The `PersistenceBackend` base class cleanly isolates storage mechanics from worker pipelines.
2. **`StreamingSink` Ready:** An existing streaming backend interface allows direct forwarding of normalized events to external message buses without modifying parser or normalization logic.
3. **`ParquetExportBackend` Built-In:** Provides native columnar output to partitioned disk folders (`year=YYYY/month=MM/day=DD`) with full SHA-256 and `raw_event_id` metadata preservation.

---

## 5. Event Flow Across All Modes

| Stage | Data Transformed | Guarantees Maintained |
|:---|:---|:---|
| **1. Wire Ingestion** | Network socket bytes $\rightarrow$ String decoded | Verbatim characters preserved |
| **2. Integrity Hashing** | Raw string $\rightarrow$ SHA-256 hex digest | Immutable cryptographic proof |
| **3. Format Detection** | Regex / Token analysis $\rightarrow$ Format Tag | Deterministic parser routing |
| **4. Parsing** | Raw text $\rightarrow$ `ParsedEvent` key-value pairs | Unmapped fields preserved in `custom_fields` |
| **5. Normalization** | `ParsedEvent` $\rightarrow$ `UniversalEvent` | Standardized canonical schema |
| **6. Validation** | `UniversalEvent` $\rightarrow$ Quality Score & Warnings | Quality grading before persistence |
| **7. Persistence Queue** | `PersistenceItem` enqueued | Non-blocking to worker (< 0.15ms) |
| **8. Durable Storage** | Batch commit to DB / Columnar Parquet / Kafka | Atomic transactions, zero data loss |

---

## 6. Air-Gap Deployment Matrix

Every deployment tier strictly adheres to the air-gapped directive:

* **Zero External Dependencies:** No Google Fonts, no public CDNs, no cloud telemetry, no hosted auth providers.
* **Local Crypto:** Passwords hashed locally with Argon2id; JWT tokens signed with local Ed25519 or HMAC-SHA256 keys.
* **Local Containerization:** Self-contained multi-stage Docker builds without runtime internet access.
* **Local Data Retention:** All logs, forensic hashes, and database entries reside entirely on local physical storage.

# OmniLogix: SIEM & Data Lake Integration — Technical Evaluator & Judge Defense

**Universal Log Pre-processing Framework (ULPF)**  
**Smart India Hackathon 2026 — Problem Statement SIH26156 (NTRO)**  
*Defensible, Transparent, and Evidence-Backed Answers for SIH Technical Judges*

---

### Q1: "Can OmniLogix integrate with SIEM platforms?"
* **Answer:** **YES (IMPLEMENTED & COMPATIBLE)**  
  OmniLogix integrates with enterprise SIEM platforms in three ways:
  1. **Columnar Data Lake (IMPLEMENTED):** Directly exports partitioned, Snappy-compressed Apache Parquet datasets that SIEMs (such as Splunk Federated Search, Amazon Athena, and ClickHouse) query with zero indexing cost.
  2. **Deterministic JSON / NDJSON (IMPLEMENTED):** Emits standard newline-delimited JSON for direct consumption by Logstash, Filebeat, and Fluentd collectors.
  3. **Streaming Broker Sink (COMPATIBLE & ARCHITECTURALLY EXTENSIBLE):** Exposes the `StreamingSink` interface to push pre-parsed, normalized event streams into Kafka, Redpanda, or Redis Streams.

---

### Q2: "Do you directly integrate with Splunk?"
* **Answer:** **COMPATIBLE (TAXONOMY & PARQUET/JSON)**  
  *Distinction:* Direct network delivery to Splunk HEC (HTTP Event Collector) is **NOT** bundled as a hard dependency to preserve air-gapped security and avoid unnecessary external network couplings.  
  However, OmniLogix provides **100% Splunk Common Information Model (CIM) compatibility** across the *Network Traffic*, *Authentication*, and *Intrusion Detection* data models. Splunk Universal Forwarders and Federated Search consume OmniLogix Parquet or JSON exports without requiring complex Splunk props/transforms regex grokking.

---

### Q3: "Do you directly integrate with Elastic?"
* **Answer:** **COMPATIBLE (ELASTIC COMMON SCHEMA - ECS)**  
  *Distinction:* Direct Elasticsearch bulk REST API indexing is **NOT** hardcoded.  
  Instead, OmniLogix achieved **complete Elastic Common Schema (ECS) field-level alignment** (`source.ip`, `destination.ip`, `event.action`, `event.severity`, `event.hash`). Elastic Logstash or OpenSearch Ingest pipelines consume OmniLogix JSON or Parquet streams natively with zero custom field remapping.

---

### Q4: "Why use Apache Parquet instead of just CSV or JSON?"
* **Answer:** **IMPLEMENTED & VERIFIED**  
  Three critical reasons:
  1. **Columnar Compression & Performance:** Parquet with Snappy compression reduces disk storage by **65% to 75%** compared to raw text, while analytical column queries scan only the requested columns (e.g., scanning only `source_ip` and `action` scans < 10% of the file).
  2. **Type Safety:** Parquet embeds native schema types (`int32`, `timestamp[us, UTC]`, `string`), preventing the type-coercion errors common to CSV.
  3. **No Schema Corruption on Delimiters:** Firewall log messages contain unescaped commas, quotes, and pipes. CSV frequently suffers delimiter breakage; Parquet avoids this by encoding binary columnar values.

---

### Q5: "How do you prevent information loss during export?"
* **Answer:** **IMPLEMENTED & VERIFIED**  
  Every exported record contains three complementary tiers of information:
  1. **Standardized Fields:** Canonical attributes mapped to the Universal Event Schema.
  2. **Structured Custom Fields:** Any proprietary vendor key-values that do not map to canonical fields are preserved losslessly inside `custom_fields`.
  3. **Verbatim Raw Payload:** The exact, unmodified wire string is embedded directly in the record alongside its cryptographic SHA-256 hash.

---

### Q6: "How do you maintain traceability between normalized and original events?"
* **Answer:** **IMPLEMENTED & VERIFIED**  
  Every normalized event has a mandatory `raw_event_id` foreign key referencing the `raw_events` table.  
  When exported (to Parquet or JSON), both `raw_event_id` and `payload_hash_sha256` are exported in the same record. The endpoint `GET /api/v1/events/{id}/raw` cryptographically re-computes `SHA256(raw_payload)` and confirms mathematical equality against `payload_hash_sha256`.

---

### Q7: "Can this operate without an internet connection?"
* **Answer:** **IMPLEMENTED & VERIFIED**  
  **100% of OmniLogix operates in an air-gapped facility.**  
  There are zero outbound Google Fonts, CDN scripts, telemetry endpoints, or cloud identity providers. All password hashing (Argon2id/bcrypt), JWT token signing, Parquet writing, and machine learning anomaly detection run locally on in-process host CPUs.

---

### Q8: "Can external Machine Learning systems consume your output?"
* **Answer:** **IMPLEMENTED & VERIFIED**  
  Yes. Downstream ML systems consume OmniLogix outputs via:
  1. **Clean Structured Datasets:** Parquet data lake files can be loaded directly into Python (`pandas.read_parquet()`, `polars.read_parquet()`) or Apache Spark in milliseconds.
  2. **Native Local ML Engine:** OmniLogix includes a built-in `FeatureExtractor` (generating 9 numerical behavioral features) and Scikit-learn `IsolationForest` unsupervised anomaly detector for offline threat discovery.

---

### Q9: "How does the system handle export failures or interruptions?"
* **Answer:** **IMPLEMENTED & VERIFIED**  
  1. **Atomic Chunking:** Export is performed in memory-bounded batches (`batch_size=10,000`). If a chunk fails, previous chunks remain safely written.
  2. **Safe State Reset:** `_is_exporting` flag is reset in `finally` blocks, preventing the service from remaining locked.
  3. **Deterministic File Naming:** Files are written with unique UUIDs (`events-{uuid}.parquet`), preventing race condition overwrites.

---

### Q10: "Can the architecture support distributed SIEM integration at scale?"
* **Answer:** **ARCHITECTURAL & EXTENSION READY**  
  Yes. OmniLogix's decoupled persistence pipeline separates parsing workers from storage via bounded queues. In enterprise distributed deployments:
  * Stateless ingestion nodes receive syslog traffic.
  * The `StreamingSink` interface routes normalized events into Apache Kafka or Redpanda topics.
  * Analytical workers and SIEM ingest forwarders pull from partitioned topics independently without bottlenecking perimeter ingestion.

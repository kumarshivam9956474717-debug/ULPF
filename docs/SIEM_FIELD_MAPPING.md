# OmniLogix SIEM Field Compatibility & Taxonomies

**Universal Log Pre-processing Framework (ULPF)**  
**Smart India Hackathon 2026 — Problem Statement SIH26156 (NTRO)**  
*Splunk Common Information Model (CIM) & Elastic Common Schema (ECS) Crosswalk*

---

## 1. Executive Summary

OmniLogix standardizes perimeter log data into the **Universal Event Schema (UES)**. To ensure effortless downstream integration with enterprise SIEM platforms, this document details the exact field-level correspondence with the two industry standard security taxonomies:
1. **Splunk Common Information Model (CIM)**: Specifically the *Network Traffic*, *Authentication*, and *Intrusion Detection* data models.
2. **Elastic Common Schema (ECS)**: Versions 1.x and 8.x covering network, host, event, and threat field sets.

### Classification Legend:
* **`DIRECT`**: Identical field name and semantic representation. Zero transformation required.
* **`MAPPED`**: Direct 1-to-1 semantic equivalence under a different field naming convention.
* **`CUSTOM`**: Retained losslessly within `custom_fields.*` or `labels.*` object hierarchy.
* **`NOT AVAILABLE`**: Concept not applicable to perimeter network security logs.

---

## 2. Comprehensive SIEM Field Mapping Crosswalk

| OmniLogix UES Field | Splunk CIM Field / Model | Elastic ECS Field | Mapping Classification | Semantic Definition & Transformation Notes |
|:---|:---|:---|:---:|:---|
| **`event_id`** | `event_id` | `event.id` | **MAPPED** | Unique identifier generated for the normalized event. |
| **`source_event_id`** | `record_number` / `vendor_event_id` | `event.sequence` | **MAPPED** | Originating sequence ID from reporting appliance. |
| **`schema_version`** | N/A | `ecs.version` | **MAPPED** | Schema specification version (`"1.0.0"`). |
| **`timestamp`** | `_time` (epoch/ISO) | `@timestamp` | **MAPPED** | Event occurrence timestamp normalized to UTC ISO 8601. |
| **`ingestion_timestamp`** | `_indextime` | `event.ingested` | **MAPPED** | Time event was received by OmniLogix. |
| **`timezone`** | `vendor_timezone` | `event.timezone` | **MAPPED** | Originating device timezone offset. |
| **`vendor`** | `vendor` | `observer.vendor` / `event.module` | **DIRECT** | Device manufacturer (e.g., Cisco, Palo Alto). |
| **`product`** | `product` | `observer.product` / `event.dataset` | **DIRECT** | Product model/family (e.g., ASA, PAN-OS). |
| **`device_type`** | `device_type` | `observer.type` | **DIRECT** | Role: `firewall`, `ids`, `ips`, `proxy`, `vpn`. |
| **`device_id`** | `dvc_id` | `observer.serial_number` | **MAPPED** | Unique appliance hardware or cluster identifier. |
| **`hostname`** | `dvc_name` / `host` | `observer.hostname` / `host.name` | **MAPPED** | Reporting gateway host name or FQDN. |
| **`source_format`** | `sourcetype` | `event.original` format | **MAPPED** | Detected format: `syslog`, `cef`, `leef`, `json`. |
| **`source_ip`** | `src_ip` / `src` | `source.ip` | **MAPPED** | Originating session IPv4 or IPv6 address. |
| **`source_port`** | `src_port` | `source.port` | **MAPPED** | Originating Layer 4 port integer (0–65535). |
| **`destination_ip`** | `dest_ip` / `dest` | `destination.ip` | **MAPPED** | Target session IPv4 or IPv6 address. |
| **`destination_port`** | `dest_port` | `destination.port` | **MAPPED** | Target Layer 4 service port integer (0–65535). |
| **`protocol`** | `transport` / `protocol` | `network.transport` / `network.protocol` | **DIRECT** | Layer 4/7 protocol: `TCP`, `UDP`, `ICMP`, `DNS`. |
| **`username`** | `user` | `user.name` | **MAPPED** | Authenticated session actor or user account. |
| **`user_id`** | `user_id` | `user.id` | **DIRECT** | Enterprise directory identifier (SID / LDAP DN). |
| **`authentication_method`** | `app` / `auth_method` | `event.type` / `user.domain` | **MAPPED** | Auth protocol: `radius`, `tacacs`, `kerberos`. |
| **`event_type`** | `category` / `event_type` | `event.category` | **DIRECT** | High-level type: `network_traffic`, `authentication`. |
| **`action`** | `action` (`allowed`, `blocked`) | `event.action` | **DIRECT** | Enforcement action: `allow`, `block`, `drop`. |
| **`outcome`** | `status` (`success`, `failure`) | `event.outcome` | **MAPPED** | Result: `success`, `failure`, `unknown`. |
| **`severity`** | `severity` | `event.severity` / `log.level` | **DIRECT** | Normalized rating: `low`, `medium`, `high`, `critical`. |
| **`category`** | `category` | `rule.category` | **DIRECT** | Taxonomy categorization (e.g., `policy_violation`). |
| **`subcategory`** | `subcategory` | `rule.sub_category` | **DIRECT** | Granular sub-category (e.g., `port_scan`). |
| **`interface`** | `src_interface` / `dest_interface` | `observer.ingress.interface.name` | **MAPPED** | Network interface (e.g., `gigabitethernet0/1`). |
| **`direction`** | `direction` (`inbound`, `outbound`) | `network.direction` | **DIRECT** | Session flow: `inbound`, `outbound`, `internal`. |
| **`zone`** | `src_zone` / `dest_zone` | `network.source.zone` | **MAPPED** | Security zone boundary (e.g., `DMZ`, `internal`). |
| **`threat_name`** | `threat_name` / `signature` | `threat.indicator.name` | **MAPPED** | Name of detected exploit, malware, or rule. |
| **`threat_id`** | `threat_id` / `cve` | `threat.indicator.reference` | **MAPPED** | Threat tracking identifier or CVE number. |
| **`signature_id`** | `signature_id` | `rule.id` | **MAPPED** | Snort, Suricata, or vendor signature ID. |
| **`rule_id`** | `rule` / `rule_name` | `rule.name` / `rule.uuid` | **MAPPED** | Security policy access-list rule identifier. |
| **`message`** | `message` / `description` | `message` | **DIRECT** | Descriptive human-readable log message text. |
| **`tags`** | `tag` | `tags` | **DIRECT** | Categorization labels array. |
| **`custom_fields`** | Key-value pairs indexed into CIM | `labels.*` / `vendor.*` | **CUSTOM** | Lossless preservation of unmapped vendor fields. |
| **`raw_event_id`** | `raw_event_id` | `event.hash` / `custom.raw_id` | **CUSTOM** | Immutable foreign key to raw wire log record. |
| **`raw_event`** | `_raw` | `event.original` | **MAPPED** | Unmodified inbound log string exactly as received. |
| **`payload_hash_sha256`** | `sha256_hash` | `event.hash` / `file.hash.sha256` | **MAPPED** | SHA-256 cryptographic digest of `raw_event`. |

---

## 3. SIEM Ingestion Compatibility Patterns

### Pattern A: Parquet Cold Storage & SIEM Data Lake
* **Technology:** Splunk Federated Search, Amazon Athena, Snowflake, Databricks, ClickHouse.
* **Mechanism:** OmniLogix writes Snappy-compressed Parquet files into `year=YYYY/month=MM/day=DD/` folder partitions.
* **Benefit:** SIEMs run distributed columnar SQL queries directly over OmniLogix Parquet datasets at zero per-gigabyte indexing cost.

### Pattern B: JSON / NDJSON Bulk Ingestion
* **Technology:** Elastic Logstash, Filebeat, OpenSearch Data Prepper, Wazuh, Splunk Universal Forwarder.
* **Mechanism:** OmniLogix emits deterministic newline-delimited JSON (NDJSON) with standard ECS/CIM key mappings.
* **Benefit:** No custom regex grok patterns needed in Logstash or Splunk; fields land in native SIEM indexes immediately.

### Pattern C: Streaming Broker Ingestion
* **Technology:** Apache Kafka, Redpanda, Redis Streams.
* **Mechanism:** The `StreamingSink` interface routes normalized event envelopes into target broker topics.
* **Benefit:** Downstream analytical consumers subscribe to pre-parsed, validated, and normalized event streams in real time.

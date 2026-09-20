# OmniLogix ULPF — Complete API Security & RBAC Matrix

This matrix documents the server-side access control, privilege requirements, and security rationales for every REST API endpoint in the OmniLogix Universal Log Pre-Processing Framework (ULPF).

All authorizations are strictly enforced **server-side** via cryptographic HMAC-SHA256 JWT tokens and parameterized FastAPI dependency gates (`require_roles`).

---

## Access Classification Levels

| Level | Description |
| :--- | :--- |
| **PUBLIC** | Unrestricted access. Strictly limited to container health checks, API docs, and the initial authentication challenge. |
| **AUTHENTICATED** | Requires a valid, cryptographically verified, non-expired JWT Bearer token from an active account (any valid role). |
| **ROLE-RESTRICTED** | Requires a valid JWT Bearer token with specific server-verified RBAC privileges (**ADMIN**, **ANALYST**, or **OPERATOR**). |

---

## Complete Endpoint Security Matrix

| Endpoint | Method | Access Level | Permitted Roles | Security Rationale |
| :--- | :---: | :---: | :---: | :--- |
| `/api/v1/health` | `GET` | **PUBLIC** | All / Anonymous | Required by Docker Compose, Kubernetes, and orchestration liveness/readiness probes. |
| `/` | `GET` | **PUBLIC** | All / Anonymous | Root metadata and health status redirect. |
| `/docs` | `GET` | **PUBLIC** | All / Anonymous | Interactive OpenAPI / Swagger documentation interface. |
| `/redoc` | `GET` | **PUBLIC** | All / Anonymous | ReDoc API specification documentation. |
| `/openapi.json` | `GET` | **PUBLIC** | All / Anonymous | Machine-readable OpenAPI JSON schema definition. |
| `/api/v1/auth/login` | `POST` | **PUBLIC** | All / Anonymous | Initial credential verification. Validates salted bcrypt hash and issues short-lived JWT access token. |
| `/api/v1/auth/me` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Returns current authenticated user profile, active state, and assigned RBAC role. |
| `/api/v1/auth/users` | `GET` | **ROLE-RESTRICTED** | **ADMIN** | System user enumeration and access governance auditing. |
| `/api/v1/auth/users` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | User provisioning and role assignment. Hashes passwords with 12-round bcrypt. |
| `/api/v1/auth/users/{id}/role` | `PUT` | **ROLE-RESTRICTED** | **ADMIN** | Privilege elevation and role modification. Protects against demoting the last active administrator. |
| `/api/v1/auth/users/{id}` | `DELETE` | **ROLE-RESTRICTED** | **ADMIN** | Account deprovisioning. Prevents self-deletion and deletion of the final remaining administrator. |
| `/api/v1/detect-format` | `POST` | **ROLE-RESTRICTED** | **ADMIN, OPERATOR, ANALYST** | Stateless heuristic format detector (CEF, LEEF, Syslog, JSON, KV). Consumes CPU/memory resources. |
| `/api/v1/ingest` | `POST` | **ROLE-RESTRICTED** | **ADMIN, OPERATOR** | Perimeter log ingestion and normalization pipeline. Persists raw and normalized records to database. |
| `/api/v1/ingest/batch` | `POST` | **ROLE-RESTRICTED** | **ADMIN, OPERATOR** | Bulk log ingestion creating operational processing run records. |
| `/api/v1/syslog/status` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Read-only telemetry: listener ports, active connections, queue depth, and drop counters. |
| `/api/v1/syslog/start` | `POST` | **ROLE-RESTRICTED** | **ADMIN, OPERATOR** | Ingestion service control: binds UDP/TCP/TLS sockets and initializes background ingestion worker tasks. |
| `/api/v1/syslog/stop` | `POST` | **ROLE-RESTRICTED** | **ADMIN, OPERATOR** | Ingestion service control: gracefully halts perimeter network listeners and flushes worker queues. |
| `/api/v1/syslog/metrics/reset` | `POST` | **ROLE-RESTRICTED** | **ADMIN, OPERATOR** | Resets telemetry counters and message statistics before benchmark or test runs. |
| `/api/v1/sources` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Lists perimeter devices, firewalls, and proxies transmitting telemetry into OmniLogix. |
| `/api/v1/sources` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Registers a new perimeter device into the system source registry. |
| `/api/v1/parsers` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Lists modular parser plug-ins, supported formats, and active versions. |
| `/api/v1/parsers` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Registers a new modular parser plug-in into the parser registry. |
| `/api/v1/onboarding/analyze` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Offline structure analysis and UES mapping recommendations on sample log payloads. |
| `/api/v1/onboarding/validate-mapping` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Simulates mapping extraction and normalizes samples in-memory without persistence. |
| `/api/v1/onboarding/test-profile` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Validates profile extraction and records test audit log entries. |
| `/api/v1/onboarding/profiles` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Creates a new log mapping profile in DRAFT status. |
| `/api/v1/onboarding/profiles` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Queries existing log mapping profiles filtered by vendor or lifecycle status. |
| `/api/v1/onboarding/profiles/{id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves complete profile configuration, field mappings, and audit history. |
| `/api/v1/onboarding/profiles/{id}` | `PUT` | **ROLE-RESTRICTED** | **ADMIN** | Updates profile regex/delimiter configurations and increments version evolution. |
| `/api/v1/onboarding/profiles/{id}/activate` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Activates profile, compiling regex and loading it into live perimeter pipeline execution. |
| `/api/v1/onboarding/profiles/{id}/disable` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Deactivates profile, removing it from live parsing pipeline. |
| `/api/v1/onboarding/profiles/{id}/versions` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Audits historical version changes, schema updates, and author attribution. |
| `/api/v1/events` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Paginated query of normalized events conforming to Universal Event Schema. |
| `/api/v1/events/{id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves single normalized security event record. |
| `/api/v1/events/{id}/raw` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Resolves 1-to-1 raw event pointer and performs real-time cryptographic SHA-256 integrity verification. |
| `/api/v1/processing-runs/{id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves operational batch execution telemetry, record counts, and parser performance. |
| `/api/v1/analytics/export` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Triggers chunked Parquet export to disk/data lake with partition directories. |
| `/api/v1/analytics/export/status` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Reads telemetry and file metadata from the latest Parquet export job. |
| `/api/v1/analytics/overview` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Dashboard throughput, anomaly rates, and normalization efficiency counters. |
| `/api/v1/analytics/timeline` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Hourly time-bucketed event telemetry series. |
| `/api/v1/analytics/vendors` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Aggregated security event distribution by vendor. |
| `/api/v1/analytics/severity` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Security event breakdown by normalized severity (LOW, MEDIUM, HIGH, CRITICAL). |
| `/api/v1/analytics/categories` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Security event distribution by MITRE/UES category. |
| `/api/v1/analytics/top-ips` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Top source IP addresses observed across perimeter firewalls. |
| `/api/v1/analytics/top-ports` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Top targeted destination network ports. |
| `/api/v1/analytics/sources` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Aggregation of events grouped by perimeter device type. |
| `/api/v1/security-analytics/overview` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | High-level data quality index, finding counts, and sensor health telemetry. |
| `/api/v1/security-analytics/trends` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Volume and anomaly trend analytics over 24h, 7d, or 30d timeframes. |
| `/api/v1/security-analytics/sources` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Evaluates log emitter heartbeat status (HEALTHY, DEGRADED, SUSPICIOUS, INACTIVE). |
| `/api/v1/security-analytics/coverage` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Negative-space analysis: identifies unmonitored enclaves and telemetry blind spots. |
| `/api/v1/security-analytics/baselines` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | 14-day historical volume baselines and z-score standard deviation metrics. |
| `/api/v1/security-analytics/correlations` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Cross-source correlation candidate clusters matching on IP, asset, or port within time windows. |
| `/api/v1/security-analytics/analyze` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Executes full security intelligence scan updating findings, baselines, and correlation clusters. |
| `/api/v1/security-analytics/findings` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Paginated supervisory findings ordered by priority score. |
| `/api/v1/security-analytics/findings/report` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Structured security report with analytical methodology, disclaimer, and findings. |
| `/api/v1/security-analytics/findings/export` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Exports findings report in JSON or CSV format. |
| `/api/v1/security-analytics/findings/{id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Detailed supervisory finding metadata, affected source, and evidence pointers. |
| `/api/v1/security-analytics/findings/{id}/review` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Examiner workflow: updates finding lifecycle state to REVIEWED with human review notes. |
| `/api/v1/security-analytics/findings/{id}/dismiss` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Examiner workflow: dismisses finding as expected operational behavior or false positive. |
| `/api/v1/supervisory/entities` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Lists monitored CSE perimeter command enclaves available for assessment. |
| `/api/v1/supervisory/entities/{id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Detailed status and sensor coverage for a monitored enclave entity. |
| `/api/v1/supervisory/assessment/{id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Comprehensive multi-dimensional supervisory assessment and execution indicators. |
| `/api/v1/supervisory/analyze` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Triggers on-demand supervisory evaluation generating entity capability scores. |
| `/api/v1/supervisory/indicators` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Lists supervisory findings and operational execution gap indicators. |
| `/api/v1/supervisory/samples` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves prioritized alert samples for supervisory review (PRIORITY 1, 2, 3, ROUTINE). |
| `/api/v1/supervisory/peer-comparison` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Entity vs peer benchmark comparison matrix across monitored organizations. |
| `/api/v1/supervisory/trends` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Period-over-period supervisory trend analysis. |
| `/api/v1/supervisory/evidence/{finding_id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves 6-level evidence chain (Finding $\rightarrow$ Indicator $\rightarrow$ Metrics $\rightarrow$ Normalized Event $\rightarrow$ Raw Event $\rightarrow$ SHA-256). |
| `/api/v1/supervisory/review/{finding_id}` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Submits human examiner review, status update, and notes for a supervisory indicator. |
| `/api/v1/supervisory/report` | `GET/POST` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Downloads supervisory report distinguishing SYSTEM-GENERATED ANALYTICS from HUMAN CONCLUSIONS. |
| `/api/v1/anomaly/train` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Fits unsupervised Isolation Forest baseline on normalized database records. |
| `/api/v1/anomaly/scan` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Evaluates normalized logs against baseline, computing anomaly scores and structured explanations. |
| `/api/v1/anomaly/results` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves anomaly scoring records, contamination ratings, and decision tree explanations. |
| `/api/v1/anomaly/results/{event_id}` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves anomaly score and decision path for a specific universal event. |
| `/api/v1/anomaly/statistics` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Anomaly frequency rate, total evaluated, contamination parameters, and training timestamp. |
| `/api/v1/demo/reset` | `POST` | **ROLE-RESTRICTED** | **ADMIN** | Safely deletes synthetic demonstration records without wiping system configuration. |
| `/api/v1/demo/load` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | Generates and loads synthetic demonstration dataset covering Scenarios A-J across 5 CSE entities. |
| `/api/v1/demo/run` | `POST` | **ROLE-RESTRICTED** | **ADMIN, ANALYST** | 1-Click end-to-end evaluation pipeline: normalization $\rightarrow$ analytics $\rightarrow$ assessment $\rightarrow$ validation. |
| `/api/v1/demo/data-quality` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Epistemic data quality evaluations distinguishing NO EVIDENCE, EVIDENCE OF ABSENCE, and INSUFFICIENT DATA. |
| `/api/v1/demo/status` | `GET` | **AUTHENTICATED** | ADMIN, ANALYST, OPERATOR, VIEWER | Retrieves demonstration mode state, loaded event counts, and scenario pass/fail metrics. |

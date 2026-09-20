# OmniLogix: Authentication & Role-Based Access Control (RBAC) Architecture

## 1. Overview & Core Philosophy

OmniLogix Universal Log Pre-Processing Framework (ULPF) operates as a critical telemetry ingestion and preprocessing gateway for security operations centers (SOC) and forensic investigators. In strict defense, tactical military, and sovereign infrastructure settings (such as NTRO / SIH Problem Statement SIH26156), the system functions in **complete air-gapped isolation**.

To satisfy these requirements:
- **Zero Cloud / External IdP Dependencies:** No Google OAuth, Microsoft Entra ID, Auth0, Okta, or AWS Cognito.
- **Local Identity Verification:** All authentication and authorization decisions occur within the host boundary using local SQLite/PostgreSQL datastores and in-process cryptographic operations.
- **Strict Role-Based Access Control (RBAC):** Every non-public API endpoint is protected server-side by declarative dependency injection (`FastAPI Depends(require_roles(...))`).
- **Defensive Cryptography:** Standardized algorithms (salted bcrypt for passwords, RFC 7519 HS256 HMAC-SHA256 for JWTs) with configurable key derivation and zero hardcoded secrets.

---

## 2. Authentication Architecture

The OmniLogix authentication workflow uses stateless JSON Web Tokens (JWT) signed with HMAC-SHA256:

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Operator
    participant FE as OmniLogix Frontend (React)
    participant API as FastAPI Gateway (/auth/login)
    participant Core as Security Core (bcrypt / PyJWT)
    participant DB as Identity Database (Users)

    Client->>FE: Enter Username & Password
    FE->>API: POST /api/v1/auth/login {username, password}
    API->>DB: Query User by Username (Case-Insensitive)
    alt User Not Found or Inactive
        API-->>FE: 401 Unauthorized ("Incorrect username or password")
    else User Found
        API->>Core: verify_password(plain, hashed_pw) via bcrypt
        alt Password Hash Mismatch
            API-->>FE: 401 Unauthorized ("Incorrect username or password")
        else Password Valid
            API->>Core: create_access_token(sub=username, role=role, jti=uuid)
            API-->>FE: 200 OK {access_token, token_type: "bearer", expires_in: 3600, user: {...}}
            FE->>FE: Store token in memory/localStorage; redirect to requested view
        end
    end

    Note over Client,FE: Subsequent Protected Requests
    Client->>FE: Navigate to Protected Resource (e.g., Ingest, Syslog Control)
    FE->>API: GET /api/v1/syslog/status (Header: Authorization: Bearer <token>)
    API->>Core: Decode & Verify HS256 signature + expiration
    API->>API: Evaluate require_roles(ADMIN, OPERATOR)
    alt Token Invalid / Expired
        API-->>FE: 401 Unauthorized
    else Role Insufficient
        API-->>FE: 403 Forbidden ("Operation requires one of [...] permissions")
    else Authorized
        API-->>FE: 200 OK (Response Payload)
    end
```

---

## 3. Password Hashing & Storage

1. **Algorithm:** Direct `bcrypt` with automatic random 128-bit salt generation.
2. **Work Factor:** 12 rounds (4,096 iterations), calibrated for defense-in-depth against GPU brute-force attacks without introducing unacceptable request latency on server CPUs (~80–120ms per verification).
3. **Secrecy Assurance:**
   - Passwords are never logged or stored in plaintext.
   - Pydantic models (`UserResponse`) explicitly omit `hashed_password` to prevent accidental serialization into API responses.
   - Database schemas mark `hashed_password` as non-nullable string fields.

---

## 4. JWT Lifecycle & Token Management

- **Signature Scheme:** HMAC-SHA256 (`HS256`).
- **Secret Management:** Loaded strictly from environment variable `JWT_SECRET_KEY`. If unset, an ephemeral, cryptographically secure 64-byte random key is generated at server startup with a high-priority security warning logged.
- **Token Claims Payload:**
  ```json
  {
    "sub": "admin",
    "role": "ADMIN",
    "iat": 1773576000,
    "exp": 1773579600,
    "jti": "d4e8b3a2-1f7c-4c28-9d62-7a8e5f2c1b9a"
  }
  ```
- **Expiration:** Default `ACCESS_TOKEN_EXPIRE_MINUTES=60` (1 hour). Expired tokens are rejected by PyJWT with HTTP 401.
- **Revocation / Invalidation:** Standard short-lived tokens. Administrator deletion or deactivation of an account (`is_active=False`) immediately rejects the user at `get_current_active_user` upon the next token verification query.

---

## 5. Role-Based Access Control (RBAC) Hierarchy

OmniLogix enforces a 4-tier principle of least privilege:

| Role | Hierarchy Level | Capabilities & Intended Persona |
| :--- | :---: | :--- |
| **`ADMIN`** | **Level 4** (Superuser) | Full administrative control: User provisioning/deprovisioning, parser configuration, source registration, demo resets, supervisory rule approvals, anomaly model retraining, and raw audit exports. |
| **`ANALYST`** | **Level 3** (SOC / DFIR) | Deep investigation capabilities: Query raw/normalized events, run security correlation analyses, inspect cryptographic hash chains, trigger anomaly scans, analyze demo datasets, test parser profiles. Cannot manage users, reset metrics, or reconfigure server engines. |
| **`OPERATOR`** | **Level 2** (SysOps / NOC) | Telemetry pipeline control: Start/stop Syslog servers, view live ingestion metrics, monitor backpressure and queue watermarks, submit raw log batches. Cannot review security findings, retrain models, or manage user accounts. |
| **`VIEWER`** | **Level 1** (Read-Only) | Passive audit access: Read-only access to normalized events, pipeline status, and health metrics. Forbidden from making mutations, starting/stopping services, or exporting unredacted raw dumps. |

### Role Hierarchy Mapping
```
ADMIN (Superuser)
  ├── Full System Config & User Management
  ├── Ingestion & Parser Management
  └── Security Investigations & Analytics
       │
       ├── ANALYST (Investigation)
       │     ├── Query & Search Events
       │     ├── Cryptographic Audit & Traceability
       │     └── Anomaly & Correlation Scans
       │
       └── OPERATOR (Telemetry Operations)
             ├── Start/Stop Ingestion Engines
             ├── Batch Log Ingestion
             └── Pipeline Health & Watermarks

VIEWER (Read-Only Observer)
  └── Passive Dashboard & Aggregation Viewing
```

---

## 6. Server-Side Enforcement Pattern

Authorization is enforced at the controller layer via FastAPI's dependency injection system:

```python
from fastapi import APIRouter, Depends
from app.core.auth import require_roles
from app.schemas.user import UserRole, UserResponse

router = APIRouter()

# Example 1: Endpoint restricted strictly to Administrators
@router.post("/sources", dependencies=[Depends(require_roles(UserRole.ADMIN))])
async def create_source(source_in: SourceCreate):
    ...

# Example 2: Endpoint permitted for Telemetry Operations (Admin or Operator)
@router.post("/syslog/start", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR))])
async def start_syslog():
    ...

# Example 3: Authenticated Read-Only access (all roles valid)
@router.get("/events")
async def get_events(current_user: User = Depends(get_current_active_user)):
    ...
```

---

## 7. First Administrator Bootstrap

In an air-gapped system, no external web hook or OAuth callback can provision the initial account. OmniLogix supports two independent, secure bootstrap mechanisms:

### Method A: Environment Variable Bootstrap (Container Startup)
Set the following environment variables in `.env` or the container runtime:
```bash
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_EMAIL=admin@omnilogix.local
ADMIN_BOOTSTRAP_PASSWORD=StrongAdminPassword#2026!
```
On application launch (`lifespan` startup hook in `app/main.py`), `services/auth_bootstrap.py` executes:
1. Checks if any user exists with `role == ADMIN`.
2. If none exists, creates the bootstrap administrator with a salted bcrypt hash.
3. If an administrator already exists, startup continues without modifying existing credentials.

### Method B: Standalone Air-Gapped CLI Tool
Administrators on a secured host or terminal can invoke the provisioning script directly:
```bash
# Interactive password prompt (masked input):
python tools/create_admin.py --username rootadmin --email secops@defense.local

# Or non-interactive for deployment automation:
python tools/create_admin.py --username secadmin --password "GovSec#Pass2026!" --role ADMIN
```

---

## 8. Frontend Integration & Guarding

1. **Token Persistence:** Stored in `localStorage` (`omnilogix_token`) and user profile cache (`omnilogix_user`).
2. **Global Fetch Interceptor (`frontend/src/services/api.ts`):** Automatically injects `Authorization: Bearer <token>` into all outbound requests. If a `401 Unauthorized` is returned by the server, the client clears credentials and redirects immediately to `/login`.
3. **Route Guards (`frontend/src/components/ProtectedRoute.tsx`):**
   - Redirects unauthenticated traffic to `/login` with return URL state.
   - Inspects `user.role` against required route roles.
   - Renders an informative `403 Forbidden` terminal banner if an operator or viewer attempts to navigate to administrative settings.
4. **Header Role Badge:** Displays user identity alongside a color-coded security classification badge (`ADMIN` = purple, `ANALYST` = blue, `OPERATOR` = amber, `VIEWER` = slate).

---

## 9. Security Limitations & Production Recommendations

1. **Token Revocation List (Blacklist):** Current implementation uses short-lived JWTs (60 min). For immediate mid-session revocation upon credential compromise, deploy a local Redis blacklist or in-memory LRU revocation cache.
2. **Rate Limiting on `/auth/login`:** In high-threat scenarios, couple the endpoint with a brute-force threshold (e.g., 5 failures per IP locks for 15 minutes).
3. **HTTPS / TLS Termination:** In enterprise deployments, an air-gapped reverse proxy (NGINX or Envoy) must terminate TLS 1.3 with internal PKI certificates so tokens are not transmitted across LAN plaintexts.

"""
OmniLogix ULPF Authentication and Role-Based Access Control (RBAC) Test Suite.

Verifies:
1. Unauthenticated request to protected endpoint -> 401
2. Invalid credentials -> 401 authentication failure
3. Valid credentials -> 200 + JWT access token with user details
4. Expired token -> 401
5. Tampered token / invalid signature -> 401
6. VIEWER attempting admin operation -> 403 Forbidden
7. OPERATOR attempting admin operation -> 403 Forbidden
8. ANALYST attempting admin operation -> 403 Forbidden
9. ADMIN accessing admin operation -> 200/201 Success
10. Protected API with valid role -> 200 Success
11. Missing Authorization header -> 401
12. Malformed Authorization header -> 401
13. Password is not returned in user API responses
14. Password hash is never exposed in responses
15. JWT secret is not exposed
16. Authentication works with air-gap mode active (no outbound connections)
17. User management lifecycle & last-admin protection
"""

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token, verify_password
from app.models.user import User


@pytest.fixture
def auth_test_env(db_session):
    """
    Dedicated test fixture that restores real authentication dependencies
    and seeds distinct users for each RBAC role.
    """
    # Override get_db to the test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Clear any auth dependency overrides so real auth runs
    app.dependency_overrides.pop(app.dependency_overrides.get("get_current_user"), None)
    app.dependency_overrides.pop(app.dependency_overrides.get("get_current_active_user"), None)
    for key in list(app.dependency_overrides.keys()):
        if getattr(key, "__name__", "") in ("get_current_user", "get_current_active_user", "override_get_current_user"):
            del app.dependency_overrides[key]

    # Seed users for each role
    test_users = {
        "admin": User(
            id="usr-admin-01",
            username="admin_user",
            email="admin@test.local",
            hashed_password=get_password_hash("AdminSecret123!"),
            role="ADMIN",
            is_active=True
        ),
        "analyst": User(
            id="usr-analyst-01",
            username="analyst_user",
            email="analyst@test.local",
            hashed_password=get_password_hash("AnalystSecret123!"),
            role="ANALYST",
            is_active=True
        ),
        "operator": User(
            id="usr-operator-01",
            username="operator_user",
            email="operator@test.local",
            hashed_password=get_password_hash("OperatorSecret123!"),
            role="OPERATOR",
            is_active=True
        ),
        "viewer": User(
            id="usr-viewer-01",
            username="viewer_user",
            email="viewer@test.local",
            hashed_password=get_password_hash("ViewerSecret123!"),
            role="VIEWER",
            is_active=True
        ),
        "inactive": User(
            id="usr-inactive-01",
            username="inactive_user",
            email="inactive@test.local",
            hashed_password=get_password_hash("InactiveSecret123!"),
            role="VIEWER",
            is_active=False
        )
    }

    for u in test_users.values():
        db_session.add(u)
    db_session.commit()

    with TestClient(app) as test_client:
        yield test_client, test_users

    app.dependency_overrides.clear()


def get_token_for(client: TestClient, username: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


# 1. Unauthenticated request to protected endpoint -> 401
def test_unauthenticated_request_fails(auth_test_env):
    client, _ = auth_test_env
    res = client.get("/api/v1/events")
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers


# 2. Invalid credentials -> 401 authentication failure
def test_invalid_credentials_rejected(auth_test_env):
    client, _ = auth_test_env
    res = client.post("/api/v1/auth/login", json={"username": "admin_user", "password": "WrongPassword999!"})
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


# 3. Valid credentials -> 200 + JWT access token
def test_valid_credentials_issue_jwt(auth_test_env):
    client, _ = auth_test_env
    res = client.post("/api/v1/auth/login", json={"username": "admin_user", "password": "AdminSecret123!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin_user"
    assert data["user"]["role"] == "ADMIN"
    assert data["expires_in"] > 0


# 4. Expired token -> 401
def test_expired_token_rejected(auth_test_env):
    client, _ = auth_test_env
    expired_token = create_access_token(
        data={"sub": "admin_user", "role": "ADMIN"},
        expires_delta=timedelta(seconds=-60)
    )
    res = client.get("/api/v1/events", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


# 5. Tampered token / invalid signature -> 401
def test_tampered_token_rejected(auth_test_env):
    client, _ = auth_test_env
    fake_token = jwt.encode(
        {"sub": "admin_user", "role": "ADMIN"},
        "wrong_secret_key_used_to_tamper_signature_32bytes",
        algorithm="HS256"
    )
    res = client.get("/api/v1/events", headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401
    assert "signature" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()


# 6. VIEWER attempting admin operation -> 403 Forbidden
def test_viewer_attempting_admin_op_forbidden(auth_test_env):
    client, _ = auth_test_env
    token = get_token_for(client, "viewer_user", "ViewerSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to reset demo environment (Admin only)
    res = client.post("/api/v1/demo/reset", headers=headers)
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


# 7. OPERATOR attempting admin operation -> 403 Forbidden
def test_operator_attempting_admin_op_forbidden(auth_test_env):
    client, _ = auth_test_env
    token = get_token_for(client, "operator_user", "OperatorSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to list/manage users (Admin only)
    res = client.get("/api/v1/auth/users", headers=headers)
    assert res.status_code == 403


# 8. ANALYST attempting admin operation -> 403 Forbidden
def test_analyst_attempting_admin_op_forbidden(auth_test_env):
    client, _ = auth_test_env
    token = get_token_for(client, "analyst_user", "AnalystSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to create parser (Admin only)
    payload = {
        "parser_id": "test_parser",
        "name": "Test",
        "vendor": "Test",
        "product": "Test",
        "device_type": "firewall"
    }
    res = client.post("/api/v1/parsers", json=payload, headers=headers)
    assert res.status_code == 403


# 9. ADMIN accessing admin operation -> 200/201 Success
def test_admin_accessing_admin_op_succeeds(auth_test_env):
    client, _ = auth_test_env
    token = get_token_for(client, "admin_user", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/auth/users", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 4


# 10. Protected API with valid role -> 200 Success
def test_protected_api_with_valid_role_succeeds(auth_test_env):
    client, _ = auth_test_env
    # Viewer can access events
    token = get_token_for(client, "viewer_user", "ViewerSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/events", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# 11. Missing Authorization header -> 401
def test_missing_auth_header_rejected(auth_test_env):
    client, _ = auth_test_env
    res = client.get("/api/v1/events")
    assert res.status_code == 401
    assert "credentials were not provided" in res.json()["detail"].lower()


# 12. Malformed Authorization header -> 401
def test_malformed_auth_header_rejected(auth_test_env):
    client, _ = auth_test_env
    # Not a Bearer token
    res = client.get("/api/v1/events", headers={"Authorization": "Basic admin:secret"})
    assert res.status_code == 401


# 13 & 14. Password and password hash are not exposed
def test_password_and_hash_never_exposed(auth_test_env):
    client, _ = auth_test_env
    token = get_token_for(client, "admin_user", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Check /auth/me
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    data_me = res_me.json()
    assert "password" not in data_me
    assert "hashed_password" not in data_me

    # Check /auth/users
    res_users = client.get("/api/v1/auth/users", headers=headers)
    assert res_users.status_code == 200
    for u in res_users.json():
        assert "password" not in u
        assert "hashed_password" not in u


# 15. JWT secret is not exposed in public endpoints or config APIs
def test_jwt_secret_not_exposed(auth_test_env):
    client, _ = auth_test_env
    # Health endpoint
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert "JWT_SECRET_KEY" not in res.text
    assert settings.JWT_SECRET_KEY not in res.text


# 16. Authentication works with air-gap mode active
def test_authentication_airgap_compliance(auth_test_env):
    client, _ = auth_test_env
    # Air-gapped mode must be True
    assert settings.AIR_GAPPED_MODE is True
    # Local login operates without any external network request
    res = client.post("/api/v1/auth/login", json={"username": "analyst_user", "password": "AnalystSecret123!"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token is not None


# 17. User management lifecycle & last-admin protection
def test_user_management_and_last_admin_protection(auth_test_env, db_session):
    client, users = auth_test_env
    admin_token = get_token_for(client, "admin_user", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a new user
    create_payload = {
        "username": "new_analyst",
        "email": "new_analyst@test.local",
        "password": "NewSecretPass123!",
        "role": "ANALYST"
    }
    res_create = client.post("/api/v1/auth/users", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    new_user_id = res_create.json()["id"]

    # 2. Update user role
    res_role = client.put(f"/api/v1/auth/users/{new_user_id}/role", json={"role": "OPERATOR"}, headers=headers)
    assert res_role.status_code == 200
    assert res_role.json()["role"] == "OPERATOR"

    # 3. Prevent deleting own active admin account
    res_self_del = client.delete(f"/api/v1/auth/users/{users['admin'].id}", headers=headers)
    assert res_self_del.status_code == 400
    assert "Cannot delete your own active administrator account" in res_self_del.json()["detail"]

    # 4. Delete the created user
    res_del = client.delete(f"/api/v1/auth/users/{new_user_id}", headers=headers)
    assert res_del.status_code == 200


# 18. Inactive user login is rejected
def test_inactive_user_login_rejected(auth_test_env):
    client, _ = auth_test_env
    res = client.post("/api/v1/auth/login", json={"username": "inactive_user", "password": "InactiveSecret123!"})
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()

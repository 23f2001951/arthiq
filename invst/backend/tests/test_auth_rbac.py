"""Unit tests for RBAC, Email-first User Onboarding, and Admin Guards."""

import os
import pytest
from fastapi.testclient import TestClient

from invst.api.app import app
from invst.api.auth import create_access_token, hash_password, get_admin_email


@pytest.fixture(autouse=True)
def force_auth_env():
    """Ensure authentication is strictly enforced in these tests."""
    old_val = os.environ.get("ARTH_IQ_FORCE_AUTH")
    os.environ["ARTH_IQ_FORCE_AUTH"] = "1"
    yield
    if old_val is not None:
        os.environ["ARTH_IQ_FORCE_AUTH"] = old_val
    else:
        os.environ.pop("ARTH_IQ_FORCE_AUTH", None)


@pytest.fixture
def client():
    return TestClient(app)


def test_email_lookup_not_found(client):
    res = client.post("/api/auth/lookup-email", json={"email": "nonexistent_investor_999@example.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is False
    assert data["status"] == "NOT_FOUND"


import uuid

def test_admin_invite_and_user_activation_flow(client):
    # 1. Admin login
    admin_login_res = client.post("/api/auth/login", json={"email": get_admin_email(), "password": "arth"})
    assert admin_login_res.status_code == 200
    admin_data = admin_login_res.json()
    admin_token = admin_data["token"]
    assert admin_data["role"] == "admin"
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin invites a new Pro Investor with a unique email
    test_email = f"investor_{uuid.uuid4().hex[:8]}@example.com"
    invite_res = client.post(
        "/api/admin/users",
        json={"email": test_email, "name": "Rajiv Sharma", "role": "user"},
        headers=admin_headers,
    )
    assert invite_res.status_code == 200
    invited_user = invite_res.json()
    assert invited_user["email"] == test_email
    assert invited_user["status"] == "INVITED"
    assert invited_user["role"] == "user"

    # 3. User checks their email on the portal
    lookup_res = client.post("/api/auth/lookup-email", json={"email": test_email})
    assert lookup_res.status_code == 200
    assert lookup_res.json()["exists"] is True
    assert lookup_res.json()["status"] == "INVITED"

    # 4. User attempts login without setting password -> should be prompted to set password
    premature_login = client.post("/api/auth/login", json={"email": test_email, "password": "any"})
    assert premature_login.status_code == 400

    # 5. User sets password on first login
    set_pass_res = client.post(
        "/api/auth/set-password",
        json={"email": test_email, "password": "SecurePassword123!"},
    )
    assert set_pass_res.status_code == 200
    set_pass_data = set_pass_res.json()
    assert set_pass_data["status"] == "ACTIVE"
    user_token = set_pass_data["token"]
    assert user_token

    # 6. Pro Investor accesses investor endpoints -> Allowed
    user_headers = {"Authorization": f"Bearer {user_token}"}
    dash_res = client.get("/api/dashboard", headers=user_headers)
    assert dash_res.status_code == 200

    # 7. Pro Investor attempts to access Admin endpoints -> 403 Forbidden
    admin_summary_res = client.get("/api/admin/summary", headers=user_headers)
    assert admin_summary_res.status_code == 403

    admin_users_res = client.get("/api/admin/users", headers=user_headers)
    assert admin_users_res.status_code == 403

    ml_train_res = client.post("/api/ml/train", json={}, headers=user_headers)
    assert ml_train_res.status_code == 403

    health_res = client.get("/api/health", headers=user_headers)
    assert health_res.status_code == 403

    # 8. Admin accesses admin endpoints -> Allowed
    admin_summary = client.get("/api/admin/summary", headers=admin_headers)
    assert admin_summary.status_code == 200
    assert "total_users" in admin_summary.json()

    # 9. Admin suspends the user
    user_id = invited_user["id"]
    suspend_res = client.patch(
        f"/api/admin/users/{user_id}/status",
        json={"status": "SUSPENDED"},
        headers=admin_headers,
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "SUSPENDED"

    # Suspended user login is rejected
    suspended_login = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": "SecurePassword123!"},
    )
    assert suspended_login.status_code == 403

    # Clean up: Admin deletes user
    del_res = client.delete(f"/api/admin/users/{user_id}", headers=admin_headers)
    assert del_res.status_code == 200


def test_profile_and_password_update(client):
    """Test user profile retrieval, name update, and password update flow."""
    admin_login_res = client.post("/api/auth/login", json={"email": get_admin_email(), "password": "arth"})
    assert admin_login_res.status_code == 200
    admin_token = admin_login_res.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Verify /api/auth/me
    me_res = client.get("/api/auth/me", headers=admin_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == get_admin_email()
    assert me_data["role"] == "admin"

    # 2. Update profile name
    update_prof_res = client.patch(
        "/api/auth/profile",
        json={"name": "Lead Quant Admin"},
        headers=admin_headers,
    )
    assert update_prof_res.status_code == 200
    assert update_prof_res.json()["name"] == "Lead Quant Admin"

    # 3. Change password with wrong current password -> 400
    bad_pass_res = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong_password", "new_password": "NewAdminPassword99!"},
        headers=admin_headers,
    )
    assert bad_pass_res.status_code == 400

    # 4. Change password with correct current password -> 200
    change_res = client.post(
        "/api/auth/change-password",
        json={"current_password": "arth", "new_password": "NewAdminPassword99!"},
        headers=admin_headers,
    )
    assert change_res.status_code == 200
    assert change_res.json()["success"] is True

    # 5. Verify login with new password works
    new_login_res = client.post(
        "/api/auth/login",
        json={"email": get_admin_email(), "password": "NewAdminPassword99!"},
    )
    assert new_login_res.status_code == 200

    # 6. Restore original password for subsequent tests
    restore_headers = {"Authorization": f"Bearer {new_login_res.json()['token']}"}
    client.post(
        "/api/auth/change-password",
        json={"current_password": "NewAdminPassword99!", "new_password": "arth"},
        headers=restore_headers,
    )


def test_master_login_synchronized_with_admin_password(client):
    """Verify master password is identical to admin@arth.iq password and tracks updates dynamically."""
    # 1. Direct master login with initial password 'arth' (no email specified)
    res_master_initial = client.post("/api/auth/login", json={"password": "arth"})
    assert res_master_initial.status_code == 200
    data_master = res_master_initial.json()
    assert data_master["role"] == "admin"
    assert data_master["user_type"] == "ADMIN"
    assert data_master["email"] == get_admin_email()
    admin_token = data_master["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin changes password to 'UpdatedAdminSecret2026!'
    change_res = client.post(
        "/api/auth/change-password",
        json={"current_password": "arth", "new_password": "UpdatedAdminSecret2026!"},
        headers=admin_headers,
    )
    assert change_res.status_code == 200

    # 3. Old master password 'arth' MUST now be rejected on master login
    old_master_res = client.post("/api/auth/login", json={"password": "arth"})
    assert old_master_res.status_code == 401

    # 4. Old password MUST also be rejected when logging in with admin email
    old_email_res = client.post(
        "/api/auth/login",
        json={"email": get_admin_email(), "password": "arth"},
    )
    assert old_email_res.status_code == 401

    # 5. New password MUST succeed on master direct login
    new_master_res = client.post("/api/auth/login", json={"password": "UpdatedAdminSecret2026!"})
    assert new_master_res.status_code == 200
    new_master_data = new_master_res.json()
    assert new_master_data["role"] == "admin"
    assert new_master_data["email"] == get_admin_email()
    new_admin_token = new_master_data["token"]

    # 6. New password MUST succeed when logging in with admin email
    new_email_res = client.post(
        "/api/auth/login",
        json={"email": get_admin_email(), "password": "UpdatedAdminSecret2026!"},
    )
    assert new_email_res.status_code == 200

    # 7. Restore original admin password 'arth'
    restore_headers = {"Authorization": f"Bearer {new_admin_token}"}
    client.post(
        "/api/auth/change-password",
        json={"current_password": "UpdatedAdminSecret2026!", "new_password": "arth"},
        headers=restore_headers,
    )

    # 8. Verify master login with 'arth' works again
    restored_master_res = client.post("/api/auth/login", json={"password": "arth"})
    assert restored_master_res.status_code == 200


def test_market_ticker_tape_endpoint(client):
    """Verify /api/v2/market/ticker-tape returns live/database quote stream for NSE/BSE tickers."""
    res = client.get("/api/v2/market/ticker-tape")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) >= 10

    # Check key symbols are represented
    symbols = {it["symbol"] for it in items}
    assert "NIFTY 50" in symbols
    assert "SENSEX" in symbols
    assert "RELIANCE" in symbols
    assert "TCS" in symbols

    for it in items:
        assert "symbol" in it
        assert "price" in it
        assert "change" in it
        assert "isPositive" in it
        assert isinstance(it["isPositive"], bool)


def test_invalid_email_format_validation(client):
    """Verify malformed email addresses receive 400 Bad Request with a clear message."""
    invalid_emails = ["notanemail", "user@", "@domain.com", "missingdot@domain", "   "]
    for bad_email in invalid_emails:
        res = client.post("/api/auth/lookup-email", json={"email": bad_email})
        assert res.status_code == 400
        data = res.json()
        assert "detail" in data
        assert "valid email" in data["detail"].lower()


def test_validation_error_handler_message_format(client):
    """Verify Pydantic validation errors return clean human-readable detail, not 500."""
    # Omit required 'email' field in EmailLookupRequest
    res = client.post("/api/auth/lookup-email", json={})
    assert res.status_code == 422
    data = res.json()
    assert "detail" in data
    assert "email" in data["detail"].lower()
    assert data.get("error_type") == "ValidationError"


def test_login_with_unregistered_email_returns_correct_message(client):
    """Verify logging in with an unregistered email returns 401 with a specific message."""
    res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent_user_xyz@institution.com", "password": "SecretPassword123"},
    )
    assert res.status_code == 401
    data = res.json()
    assert "detail" in data
    assert "No account registered with email" in data["detail"]


def test_database_connection_fallback_to_sqlite():
    """Verify get_db_connection falls back to local SQLite when Postgres is unreachable."""
    from invst.db.engine import get_db_connection
    # Pass an unreachable postgres url
    conn = get_db_connection(db_url="postgresql://invalid_user:invalid_pass@127.0.0.1:59999/fake_db")
    assert conn is not None
    # Verify it falls back to a working connection that can execute a query
    cur = conn.cursor()
    cur.execute("SELECT 1")
    row = cur.fetchone()
    assert row[0] == 1
    conn.close()


def test_unregistered_email_lookup_returns_not_found(client):
    """Verify entering an unregistered email (e.g. abc@gmail.com) returns NOT_FOUND status."""
    res = client.post("/api/auth/lookup-email", json={"email": "abc@gmail.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is False
    assert data["status"] == "NOT_FOUND"
    assert data["email"] == "abc@gmail.com"




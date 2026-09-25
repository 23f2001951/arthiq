"""Integration tests for Arth IQ authentication system."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from invst.api.app import create_app
from invst.api.auth import (
    get_admin_email,
    get_master_password,
    hash_password,
    init_users_table,
    verify_password,
)
from invst.api.routes import get_db



@pytest.fixture
def auth_client(scoring_db: sqlite3.Connection):
    """Test client with db override and forced authentication enforcement."""
    app = create_app()

    # Seed master admin (admin@arth.iq) into in-memory test database
    init_users_table(scoring_db)
    admin_email = get_admin_email()
    p_hash = hash_password("arth")
    scoring_db.execute(
        "UPDATE users SET password_hash = ?, status = 'ACTIVE' WHERE LOWER(email) = LOWER(?)",
        (p_hash, admin_email),
    )
    scoring_db.commit()

    def override_get_db():
        yield scoring_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


def test_auth_password_verification(scoring_db: sqlite3.Connection):
    init_users_table(scoring_db)
    admin_email = get_admin_email()
    p_hash = hash_password("arth")
    scoring_db.execute(
        "UPDATE users SET password_hash = ?, status = 'ACTIVE' WHERE LOWER(email) = LOWER(?)",
        (p_hash, admin_email),
    )
    scoring_db.commit()

    assert verify_password("arth", conn=scoring_db) is True
    assert verify_password("wrong", conn=scoring_db) is False
    assert get_master_password() == ""



def test_login_success_and_verify(auth_client: TestClient):
    # 1. Attempt login with correct password
    resp = auth_client.post("/api/auth/login", json={"password": "arth"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    token = data["token"]
    assert data["status"] == "authenticated"

    # 2. Verify token
    v_resp = auth_client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["authenticated"] is True

    # 3. Access protected dashboard with token
    dash_resp = auth_client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash_resp.status_code == 200

    # 4. Logout
    logout_resp = auth_client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "logged_out"

    # 5. Verify after logout
    v_resp_after = auth_client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert v_resp_after.status_code == 200
    assert v_resp_after.json()["authenticated"] is False


def test_login_failure(auth_client: TestClient):
    resp = auth_client.post("/api/auth/login", json={"password": "wrong_password"})
    assert resp.status_code == 401
    assert "Incorrect administrator password" in resp.json()["detail"]


def test_invalid_token_rejected(auth_client: TestClient):
    resp = auth_client.get("/api/dashboard", headers={"Authorization": "Bearer non_existent_token_12345"})
    assert resp.status_code == 401
    assert "Session expired or invalid" in resp.json()["detail"]

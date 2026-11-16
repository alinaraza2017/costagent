"""Registration, login, and profile behavior."""

from app.database import SessionLocal
from app.models import User
from tests.conftest import auth_header


def test_register_login_me_and_logout(client):
    headers = auth_header(client, "ada@example.com", full_name="Ada Lovelace")
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Lovelace"
    assert body["ai_mode"] == "rule_based"
    logged_out = client.post("/api/auth/logout", headers=headers)
    assert logged_out.status_code == 200
    rejected = client.get("/api/auth/me", headers=headers)
    assert rejected.status_code == 401


def test_login_failure_is_generic(client):
    auth_header(client, "ada@example.com")
    missing = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "Secret123"})
    wrong = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "Wrong123"})
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json()["detail"] == wrong.json()["detail"] == "Invalid email or password"


def test_profile_omits_password_hash(client):
    headers = auth_header(client, "ada@example.com", password="Secret123")
    me = client.get("/api/auth/me", headers=headers)
    assert "password" not in me.text.lower()
    assert "$2" not in me.text
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "ada@example.com").one()
        assert user.password_hash != "Secret123"
        assert user.password_hash.startswith("$2")
    finally:
        db.close()


def test_duplicate_registration_and_password_rules(client):
    auth_header(client, "ada@example.com")
    duplicate = client.post(
        "/api/auth/register",
        json={"email": "ada@example.com", "full_name": "Ada", "password": "Secret123"},
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "full_name": "New User", "password": "password"},
    )
    assert weak.status_code == 422


def test_change_password_and_profile_name(client):
    headers = auth_header(client, "ada@example.com", password="Secret123", full_name="Ada")
    renamed = client.put("/api/auth/me", json={"full_name": "Ada Lovelace"}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.json()["full_name"] == "Ada Lovelace"
    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "Secret123", "new_password": "Better123"},
        headers=headers,
    )
    assert changed.status_code == 200
    old = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "Secret123"})
    new = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "Better123"})
    assert old.status_code == 401
    assert new.status_code == 200

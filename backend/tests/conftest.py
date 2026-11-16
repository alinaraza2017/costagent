"""Isolated SQLite database and test client for the API suite."""

import os
import tempfile
from pathlib import Path

_db_path = Path(tempfile.mkdtemp(prefix="costwise-tests-")) / "test.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.as_posix()
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-use"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["LOGIN_RATE_LIMIT"] = "5/minute"
os.environ["REGISTER_RATE_LIMIT"] = "30/minute"
os.environ["SENSITIVE_RATE_LIMIT"] = "60/minute"
os.environ["LLM_API_KEY"] = ""
os.environ["DEBUG"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["MAX_UPLOAD_BYTES"] = str(5 * 1024 * 1024)
os.environ["MAX_IMPORT_ROWS"] = "500"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.limiter import limiter
from app.main import app


@pytest.fixture(autouse=True)
def reset_state():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_header(client: TestClient, email: str, password: str = "Secret123", full_name: str = "Test User") -> dict:
    created = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert created.status_code == 201, created.text
    logged_in = client.post("/api/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200, logged_in.text
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


def create_project(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {
        "name": "Library Sensors",
        "description": "Fictional sensor rollout",
        "start_date": "2026-01-10",
        "end_date": "2026-04-30",
        "budget": 500000,
        "currency": "PKR",
        "status": "active",
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()

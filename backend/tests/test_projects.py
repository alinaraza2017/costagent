"""Projects, expenses, and aggregate calculations exposed by the API."""

from app.database import SessionLocal
from app.models import Expense
from tests.conftest import auth_header, create_project


def _expense(name, estimated, actual, category="Equipment", expense_date="2026-02-01"):
    return {
        "expense_name": name,
        "category": category,
        "description": "Fictional cost",
        "estimated_cost": estimated,
        "actual_cost": actual,
        "expense_date": expense_date,
        "vendor": "Campus Stores",
    }


def test_project_and_expense_crud(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    created = client.post(f"/api/projects/{project['id']}/expenses", json=_expense("Sensors", 100, 150), headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["variance"] == 50
    assert body["percentage_variance"] == 50
    assert body["variance_interpretation"] == "Actual cost exceeded the estimate"

    updated = client.put(
        f"/api/expenses/{body['id']}",
        json=_expense("Sensors", 100, 80),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["variance"] == -20
    assert updated.json()["variance_interpretation"] == "Actual cost was below the estimate"

    listed = client.get(f"/api/projects/{project['id']}/expenses", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    removed = client.delete(f"/api/expenses/{body['id']}", headers=headers)
    assert removed.status_code == 204
    after = client.get(f"/api/projects/{project['id']}/expenses", headers=headers)
    assert after.json()["total"] == 0

    deleted = client.delete(f"/api/projects/{project['id']}", headers=headers)
    assert deleted.status_code == 204
    missing = client.get(f"/api/projects/{project['id']}", headers=headers)
    assert missing.status_code == 404


def test_zero_estimate_percentage_is_null(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    response = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Unplanned adapter", 0, 50, category="Other"),
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["percentage_variance"] is None
    assert response.json()["variance"] == 50


def test_project_summary_uses_aggregate_percentage(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    client.post(f"/api/projects/{project['id']}/expenses", json=_expense("Small", 10, 40, category="Other"), headers=headers)
    client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Large", 1000, 1000, category="Software", expense_date="2026-02-02"),
        headers=headers,
    )
    summary = client.get(f"/api/projects/{project['id']}/analytics", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_estimated"] == 1010
    assert body["total_actual"] == 1040
    assert body["percentage_variance"] == 2.97
    assert body["percentage_variance"] != 150


def test_invalid_project_dates_and_negative_cost(client):
    headers = auth_header(client, "owner@example.com")
    response = client.post(
        "/api/projects",
        json={
            "name": "Bad dates",
            "description": "",
            "start_date": "2026-05-01",
            "end_date": "2026-01-01",
            "budget": 10,
            "currency": "PKR",
            "status": "planning",
        },
        headers=headers,
    )
    assert response.status_code == 422
    project = create_project(client, headers, name="Valid")
    negative = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Refund", -5, 10),
        headers=headers,
    )
    assert negative.status_code == 422
    bad_date = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Broken date", 10, 10, expense_date="not-a-date"),
        headers=headers,
    )
    assert bad_date.status_code == 422


def test_users_only_see_their_projects(client):
    owner = auth_header(client, "owner@example.com")
    other = auth_header(client, "other@example.com", full_name="Other User")
    create_project(client, owner, name="Owner project")
    create_project(client, other, name="Other project")
    owner_list = client.get("/api/projects", headers=owner)
    other_list = client.get("/api/projects", headers=other)
    assert [item["name"] for item in owner_list.json()["items"]] == ["Owner project"]
    assert [item["name"] for item in other_list.json()["items"]] == ["Other project"]


def test_delete_project_removes_expenses(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    client.post(f"/api/projects/{project['id']}/expenses", json=_expense("Sensors", 10, 10), headers=headers)
    client.delete(f"/api/projects/{project['id']}", headers=headers)
    db = SessionLocal()
    try:
        assert db.query(Expense).count() == 0
    finally:
        db.close()

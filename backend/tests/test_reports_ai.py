"""Charts, rule-based insights, and report content."""

from types import SimpleNamespace

from app.services.ai_analysis import _anomalies
from tests.conftest import auth_header, create_project


def _expense(name, category, estimated, actual, expense_date):
    return {
        "expense_name": name,
        "category": category,
        "description": "Fictional",
        "estimated_cost": estimated,
        "actual_cost": actual,
        "expense_date": expense_date,
        "vendor": "Campus Stores",
    }


def test_charts_come_from_saved_records(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers, name="Chart Project")
    client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Licenses", "Software", 100, 130, "2026-01-15"),
        headers=headers,
    )
    client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Travel day", "Travel", 80, 50, "2026-02-15"),
        headers=headers,
    )
    charts = client.get(f"/api/projects/{project['id']}/charts", headers=headers)
    assert charts.status_code == 200, charts.text
    body = charts.json()
    labels = {point["label"]: point for point in body["by_category"]}
    assert labels["Software"]["estimated"] == 100
    assert labels["Software"]["actual"] == 130
    assert labels["Travel"]["variance"] == -30
    assert body["spending_over_time"][1]["cumulative_actual"] == 180
    filtered = client.get(
        "/api/analytics/charts",
        params={"project_id": project["id"], "category": "Travel"},
        headers=headers,
    )
    assert [point["label"] for point in filtered.json()["by_category"]] == ["Travel"]


def test_rule_based_anomaly_needs_peers_and_flags_outlier():
    def row(row_id, actual, name):
        return SimpleNamespace(
            id=row_id,
            category="Equipment",
            expense_name=name,
            estimated_cost=100,
            actual_cost=actual,
        )

    small = [row(1, 100, "A"), row(2, 900, "B")]
    anomalies, notes = _anomalies(small)
    assert anomalies == []
    assert notes and "too few" in notes[0]["message"]

    peers = [100000, 110000, 120000, 130000, 140000, 900000]
    rows = [row(index + 1, amount, f"Item {index}") for index, amount in enumerate(peers)]
    anomalies, notes = _anomalies(rows)
    assert notes == []
    assert len(anomalies) == 1
    assert anomalies[0]["expense_name"] == "Item 5"
    assert "not evidence of fraud" in anomalies[0]["reason"]


def test_analysis_and_pdf_for_owner(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers, name="Insight Project")
    amounts = [100000, 110000, 120000, 130000, 140000, 900000]
    for index, amount in enumerate(amounts):
        client.post(
            f"/api/projects/{project['id']}/expenses",
            json=_expense(f"Device {index}", "Equipment", 100000, amount, f"2026-03-{index + 1:02d}"),
            headers=headers,
        )
    analysis = client.post(f"/api/projects/{project['id']}/ai/analyze", headers=headers)
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert body["mode_label"].startswith("Rule-based")
    assert body["highest_spending_categories"][0]["category"] == "Equipment"
    assert any(item["expense_name"] == "Device 5" for item in body["anomalies"])
    assert any(item["expense_name"] == "Device 5" for item in body["over_budget_expenses"])
    pdf = client.get(f"/api/projects/{project['id']}/reports/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert "DemoPass" not in pdf.content.decode("latin-1", errors="ignore")

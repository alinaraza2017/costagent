"""PERT analysis and project comparison."""

from tests.conftest import auth_header, create_project


def _expense(name, estimated, actual, **extra):
    payload = {
        "expense_name": name,
        "category": "Equipment",
        "description": "Fictional cost",
        "estimated_cost": estimated,
        "actual_cost": actual,
        "expense_date": "2026-02-01",
        "vendor": "Campus Stores",
    }
    payload.update(extra)
    return payload


def test_pert_formula_on_a_project(client):
    headers = auth_header(client, "pert@example.com")
    project = create_project(client, headers, budget=20)
    first = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Sensors", 10, 10, optimistic_cost=6, most_likely_cost=9, pessimistic_cost=18),
        headers=headers,
    )
    assert first.status_code == 201, first.text
    assert first.json()["pert_expected"] == 10
    assert first.json()["pert_std_dev"] == 2
    second = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Cabling", 8, 8, optimistic_cost=6, most_likely_cost=9, pessimistic_cost=18, expense_date="2026-02-02"),
        headers=headers,
    )
    assert second.status_code == 201, second.text

    analysis = client.get(f"/api/projects/{project['id']}/pert", headers=headers)
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert body["activity_count"] == 2
    assert body["missing_count"] == 0
    assert body["expected_cost"] == 20
    assert body["variance"] == 8
    assert body["std_dev"] == 2.83
    assert body["budget_probability"] == 50
    assert len(body["ranges"]) == 3


def test_pert_points_must_be_complete_and_ordered(client):
    headers = auth_header(client, "pert-rules@example.com")
    project = create_project(client, headers)
    partial = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Sensors", 10, 10, optimistic_cost=6),
        headers=headers,
    )
    assert partial.status_code == 422
    disordered = client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Sensors", 10, 10, optimistic_cost=20, most_likely_cost=9, pessimistic_cost=18),
        headers=headers,
    )
    assert disordered.status_code == 422


def test_suggest_fills_only_missing_rows(client):
    headers = auth_header(client, "pert-suggest@example.com")
    project = create_project(client, headers)
    client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Already set", 100, 100, optimistic_cost=80, most_likely_cost=100, pessimistic_cost=140),
        headers=headers,
    )
    client.post(
        f"/api/projects/{project['id']}/expenses",
        json=_expense("Needs points", 200, 0, expense_date="2026-03-01"),
        headers=headers,
    )
    suggested = client.post(f"/api/projects/{project['id']}/pert/suggest", headers=headers)
    assert suggested.status_code == 200, suggested.text
    body = suggested.json()
    assert body["suggested_count"] == 1
    assert body["activity_count"] == 2
    saved = {row["expense_name"]: row for row in body["activities"]}
    assert saved["Already set"]["optimistic_cost"] == 80
    assert saved["Needs points"]["optimistic_cost"] == 180
    assert saved["Needs points"]["most_likely_cost"] == 200
    assert saved["Needs points"]["pessimistic_cost"] == 250


def test_compare_projects_and_blocks_other_owners(client):
    owner = auth_header(client, "compare-owner@example.com")
    first = create_project(client, owner, name="Alpha Lab", budget=1000)
    second = create_project(client, owner, name="Beta Lab", budget=400)
    client.post(f"/api/projects/{first['id']}/expenses", json=_expense("Alpha item", 100, 150), headers=owner)
    client.post(
        f"/api/projects/{second['id']}/expenses",
        json=_expense("Beta item", 40, 40, optimistic_cost=30, most_likely_cost=40, pessimistic_cost=70),
        headers=owner,
    )
    same = client.get("/api/analytics/compare", params={"left_id": first["id"], "right_id": first["id"]}, headers=owner)
    assert same.status_code == 422

    compared = client.get(
        "/api/analytics/compare",
        params={"left_id": first["id"], "right_id": second["id"]},
        headers=owner,
    )
    assert compared.status_code == 200, compared.text
    body = compared.json()
    assert body["same_currency"] is True
    assert body["deltas"]["budget"] == -600
    assert body["deltas"]["total_estimated"] == -60
    assert body["deltas"]["total_actual"] == -110
    assert body["left"]["pert_expected"] is None
    assert body["right"]["pert_expected"] == 43.33
    assert body["deltas"]["pert_expected"] is None

    other = auth_header(client, "compare-other@example.com")
    denied = client.get(
        "/api/analytics/compare",
        params={"left_id": first["id"], "right_id": second["id"]},
        headers=other,
    )
    assert denied.status_code == 403


def test_compare_does_not_subtract_different_currencies(client):
    headers = auth_header(client, "compare-fx@example.com")
    pkr = create_project(client, headers, name="PKR Lab", currency="PKR", budget=100)
    usd = create_project(client, headers, name="USD Lab", currency="USD", budget=50)
    compared = client.get(
        "/api/analytics/compare",
        params={"left_id": pkr["id"], "right_id": usd["id"]},
        headers=headers,
    )
    assert compared.status_code == 200, compared.text
    body = compared.json()
    assert body["same_currency"] is False
    assert body["deltas"] is None

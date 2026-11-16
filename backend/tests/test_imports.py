"""CSV and XLSX preview, validation, and confirmation."""

import io

from openpyxl import Workbook

from app.database import SessionLocal
from app.models import Expense
from tests.conftest import auth_header, create_project

HEADER = "expense_name,category,description,estimated_cost,actual_cost,expense_date,vendor\n"


def _upload(client, headers, project_id, filename, content, column_map=None):
    files = {"file": (filename, content, "application/octet-stream")}
    data = {}
    if column_map is not None:
        data["column_map"] = column_map
    return client.post(f"/api/projects/{project_id}/imports/preview", files=files, data=data, headers=headers)


def _expense_count():
    db = SessionLocal()
    try:
        return db.query(Expense).count()
    finally:
        db.close()


def test_template_and_confirm_round_trip(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    template = client.get("/api/imports/sample-template", headers=headers)
    assert template.status_code == 200
    assert "expense_name" in template.text
    preview = _upload(client, headers, project["id"], "costs.csv", template.content)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["needs_mapping"] is False
    assert body["accepted_count"] >= 1
    assert _expense_count() == 0
    confirmed = client.post(
        f"/api/projects/{project['id']}/imports/confirm",
        json={"import_id": body["import_id"]},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["imported_count"] == body["accepted_count"]
    assert _expense_count() == body["accepted_count"]
    again = client.post(
        f"/api/projects/{project['id']}/imports/confirm",
        json={"import_id": body["import_id"]},
        headers=headers,
    )
    assert again.status_code == 409
    assert _expense_count() == body["accepted_count"]


def test_cancel_writes_nothing(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    csv_text = HEADER + "Router,Equipment,Lab router,100,90,2026-03-01,NetSupply\n"
    preview = _upload(client, headers, project["id"], "costs.csv", csv_text.encode())
    import_id = preview.json()["import_id"]
    cancelled = client.post(f"/api/projects/{project['id']}/imports/{import_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert _expense_count() == 0
    confirmed = client.post(
        f"/api/projects/{project['id']}/imports/confirm",
        json={"import_id": import_id},
        headers=headers,
    )
    assert confirmed.status_code == 409
    assert _expense_count() == 0


def test_row_errors_are_not_saved(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    csv_text = (
        HEADER
        + "Good row,Equipment,ok,100,80,2026-03-01,NetSupply\n"
        + "Bad cost,Equipment,ok,-5,80,2026-03-02,NetSupply\n"
        + "Bad date,Travel,ok,10,10,32/13/2026,Coach\n"
        + ",Software,missing name,10,10,2026-03-03,Cloud\n"
    )
    preview = _upload(client, headers, project["id"], "mixed.csv", csv_text.encode())
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["accepted_count"] == 1
    assert body["rejected_count"] == 3
    assert _expense_count() == 0
    confirmed = client.post(
        f"/api/projects/{project['id']}/imports/confirm",
        json={"import_id": body["import_id"]},
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["imported_count"] == 1
    assert _expense_count() == 1


def test_duplicate_policy(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    row = "Router,Equipment,Lab router,100,90,2026-03-01,NetSupply\n"
    preview = _upload(client, headers, project["id"], "dup.csv", (HEADER + row + row).encode())
    body = preview.json()
    assert body["accepted_count"] == 1
    assert body["duplicate_count"] == 1
    assert "duplicate" in body["duplicate_policy"].lower()
    client.post(f"/api/projects/{project['id']}/imports/confirm", json={"import_id": body["import_id"]}, headers=headers)
    second = _upload(client, headers, project["id"], "dup2.csv", (HEADER + row).encode())
    assert second.json()["duplicate_count"] == 1
    assert second.json()["accepted_count"] == 0
    assert _expense_count() == 1


def test_formula_text_is_not_executed(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    csv_text = HEADER + 'Formula,Equipment,no,=10+5,8,2026-03-01,NetSupply\n'
    preview = _upload(client, headers, project["id"], "formula.csv", csv_text.encode())
    body = preview.json()
    assert body["accepted_count"] == 0
    assert body["rejected_count"] == 1
    assert _expense_count() == 0
    joined = " ".join(error["message"] for error in body["errors"])
    assert "15" not in joined


def test_xlsx_values_import_and_formula_cells_are_rejected(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["expense_name", "category", "estimated_cost", "actual_cost", "expense_date", "vendor"])
    sheet.append(["Laptop", "Equipment", 1000, 900, "2026-04-01", "Campus Stores"])
    sheet["C3"] = "=10+5"
    sheet["A3"] = "Formula row"
    sheet["B3"] = "Software"
    sheet["D3"] = 8
    sheet["E3"] = "2026-04-02"
    buffer = io.BytesIO()
    workbook.save(buffer)
    preview = _upload(client, headers, project["id"], "costs.xlsx", buffer.getvalue())
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["accepted_count"] == 1
    assert body["rejected_count"] == 1
    names = [row["expense_name"] for row in body["valid_rows"]]
    assert names == ["Laptop"]
    assert body["valid_rows"][0]["actual_cost"] == 900


def test_estimate_file_categories_and_blank_actuals(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    csv_text = (
        "expense_name,category,description,estimated_cost,actual_cost,expense_date,vendor\n"
        '"VS Code, Python 3.11, Git",Software & Tools,Development tools,0.0,,2026-04-15,Open-source / internal\n'
        "GPT-4o-mini input tokens,AI / Cloud API,Token estimate,4200.0,,2026-04-15,OpenAI\n"
        "Developer laptops,Hardware & Infrastructure,Existing laptops,208333.33,,2026-04-15,Estimated / To be confirmed\n"
        "RAGAS evaluation API budget,Testing,Evaluation budget,4200.0,,2026-10-01,Estimated / To be confirmed\n"
        "Poster material,Documentation & Handover,Demo day,6000.0,,2027-01-15,Estimated / To be confirmed\n"
    )
    preview = _upload(client, headers, project["id"], "PropBot_Costwise_Import.csv", csv_text.encode())
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["accepted_count"] == 5
    assert body["rejected_count"] == 0
    assert body["valid_rows"][1]["actual_cost"] == 0
    assert "set to 0" in body["message"]
    categories = {row["category"] for row in body["valid_rows"]}
    assert "Software & Tools" in categories
    assert "AI / Cloud API" in categories
    assert "Documentation & Handover" in categories


def test_column_mapping(client):
    headers = auth_header(client, "owner@example.com")
    project = create_project(client, headers)
    csv_text = "Title,Group,Guess,Spent,When\nRouter,Equipment,100,90,2026-03-01\n"
    first = _upload(client, headers, project["id"], "custom.csv", csv_text.encode())
    assert first.status_code == 200
    assert first.json()["needs_mapping"] is True
    assert _expense_count() == 0
    mapping = (
        '{"expense_name":"Title","category":"Group","estimated_cost":"Guess",'
        '"actual_cost":"Spent","expense_date":"When"}'
    )
    second = _upload(client, headers, project["id"], "custom.csv", csv_text.encode(), column_map=mapping)
    assert second.status_code == 200, second.text
    assert second.json()["needs_mapping"] is False
    assert second.json()["accepted_count"] == 1


def test_optional_pert_columns_are_saved(client):
    headers = auth_header(client, "pert-import@example.com")
    project = create_project(client, headers)
    csv_text = (
        "expense_name,category,description,estimated_cost,actual_cost,expense_date,vendor,"
        "optimistic_cost,most_likely_cost,pessimistic_cost\n"
        "Architecture,Personnel,Scaled from the schedule,300000,324000,2026-06-02,Software Architect,240000,300000,440000\n"
    )
    preview = _upload(client, headers, project["id"], "pert.csv", csv_text.encode())
    assert preview.status_code == 200, preview.text
    confirmed = client.post(
        f"/api/projects/{project['id']}/imports/confirm",
        json={"import_id": preview.json()["import_id"]},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    listed = client.get(f"/api/projects/{project['id']}/expenses", headers=headers)
    row = listed.json()["items"][0]
    assert row["variance"] == 24000
    assert row["optimistic_cost"] == 240000
    assert row["most_likely_cost"] == 300000
    assert row["pessimistic_cost"] == 440000
    assert row["pert_expected"] == 313333.33

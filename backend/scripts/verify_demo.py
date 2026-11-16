"""Exercise the running local API with the fictional demo account. Prints statuses only."""

import httpx

BASE = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5173"


def main() -> None:
    with httpx.Client(timeout=30) as client:
        health = client.get(f"{BASE}/api/health")
        assert health.status_code == 200, health.text
        assert health.json()["ai_mode"] == "rule_based"
        assert health.headers["x-content-type-options"] == "nosniff"

        page = client.get(FRONTEND)
        assert page.status_code == 200
        assert "CostWise AI" in page.text

        proxied = client.get(f"{FRONTEND}/api/health")
        assert proxied.status_code == 200

        login = client.post(
            f"{BASE}/api/auth/login",
            json={"email": "demo@costwise.local", "password": "DemoPass123!"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        projects = client.get(f"{BASE}/api/projects", headers=headers)
        assert projects.status_code == 200
        items = projects.json()["items"]
        assert len(items) >= 2
        network = next(item for item in items if item["name"] == "North Campus Network Upgrade")
        project_id = network["id"]

        charts = client.get(f"{BASE}/api/projects/{project_id}/charts", headers=headers)
        assert charts.status_code == 200
        body = charts.json()
        assert any(point["label"] == "Equipment" for point in body["by_category"])
        assert body["variance_by_category"]

        analysis = client.post(f"{BASE}/api/projects/{project_id}/ai/analyze", headers=headers)
        assert analysis.status_code == 200, analysis.text
        insight = analysis.json()
        assert insight["mode"] == "rule_based"
        assert insight["anomalies"]
        assert "not evidence of fraud" in insight["anomalies"][0]["reason"]

        pdf = client.get(f"{BASE}/api/projects/{project_id}/reports/pdf", headers=headers)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        csv_file = client.get(f"{BASE}/api/projects/{project_id}/reports/csv", headers=headers)
        assert csv_file.status_code == 200
        assert "Emergency firewall appliance" in csv_file.text

        other = client.post(
            f"{BASE}/api/auth/register",
            json={"email": "other.demo@example.com", "full_name": "Other Demo", "password": "Secret123"},
        )
        if other.status_code == 409:
            other_login = client.post(
                f"{BASE}/api/auth/login",
                json={"email": "other.demo@example.com", "password": "Secret123"},
            )
        else:
            assert other.status_code == 201, other.text
            other_login = client.post(
                f"{BASE}/api/auth/login",
                json={"email": "other.demo@example.com", "password": "Secret123"},
            )
        assert other_login.status_code == 200
        other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
        denied = client.get(f"{BASE}/api/projects/{project_id}/reports/pdf", headers=other_headers)
        assert denied.status_code == 403
        assert b"%PDF" not in denied.content

        checklist = client.get(f"{BASE}/api/security/checklist", headers=headers)
        assert checklist.status_code == 200
        assert all(item["completed"] is False for item in checklist.json())

        from app.database import SessionLocal
        from app.models import ChecklistState, SecurityAuditLog, User

        db = SessionLocal()
        try:
            extra = db.query(User).filter(User.email == "other.demo@example.com").first()
            if extra is not None:
                db.query(ChecklistState).filter(ChecklistState.user_id == extra.id).delete()
                db.query(SecurityAuditLog).filter(SecurityAuditLog.user_id == extra.id).delete()
                db.delete(extra)
                db.commit()
        finally:
            db.close()

        print("live-verification-ok")


if __name__ == "__main__":
    main()

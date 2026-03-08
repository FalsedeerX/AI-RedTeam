import json
import sys
import pytest
from pathlib import Path

# add <repo_root>/backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from verification.backend import app



@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    resp = client.get("/api/health")

    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "operational"
    assert data["mode"] == "simulation"


def test_login_success(client):
    resp = client.post(
        "/api/login",
        json={
            "username": "operator",
            "password": "redteam",
        },
    )

    assert resp.status_code == 200

    data = resp.get_json()
    assert "token" in data
    assert isinstance(data["token"], str)


def test_login_failure(client):
    resp = client.post(
        "/api/login",
        json={
            "username": "operator",
            "password": "wrongpassword",
        },
    )

    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data


def test_scan_and_report_flow(client):
    login_resp = client.post(
        "/api/login",
        json={
            "username": "operator",
            "password": "redteam",
        },
    )

    assert login_resp.status_code == 200
    token = login_resp.get_json()["token"]

    scan_resp = client.post(
        "/api/scan",
        json={"target_id": "tgt-001"},
        headers={"Authorization": token},
    )

    assert scan_resp.status_code == 200

    scan_data = scan_resp.get_json()
    assert "scan_id" in scan_data
    scan_id = scan_data["scan_id"]

    # ---- retrieve report ----
    report_resp = client.get(f"/api/report/{scan_id}")

    assert report_resp.status_code == 200

    report = report_resp.get_json()

    assert report["scan_id"] == scan_id
    assert "summary" in report
    assert "findings" in report

    assert len(report["findings"]) > 0

    for finding in report["findings"]:
        assert "title" in finding
        assert "severity" in finding
        assert "confidence" in finding
        assert 0.0 <= finding["confidence"] <= 1.0


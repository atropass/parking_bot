import os
import pytest
from fastapi.testclient import TestClient

from admin.approval_service import app
from db.sql_store import init_db, create_reservation
from config.settings import SQLITE_DB_PATH, ADMIN_API_KEY


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    init_db()
    yield
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": ADMIN_API_KEY}


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_pending_reservations_empty(client, auth_headers):
    response = client.get("/admin/pending", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_pending_reservations_with_data(client, auth_headers):
    create_reservation("User 1", "AAA-111", "2026-03-10 09:00", "2026-03-10 17:00", "A")
    create_reservation("User 2", "BBB-222", "2026-03-11 10:00", "2026-03-11 18:00")

    response = client.get("/admin/pending", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["full_name"] == "User 1"
    assert data[1]["full_name"] == "User 2"


def test_get_reservation_details(client, auth_headers):
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00", "A"
    )

    response = client.get(f"/admin/reservation/{reservation_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == reservation_id
    assert data["full_name"] == "John Doe"
    assert data["status"] == "pending"


def test_get_reservation_details_not_found(client, auth_headers):
    response = client.get("/admin/reservation/999", headers=auth_headers)
    assert response.status_code == 404


def test_approve_reservation(client, auth_headers):
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response = client.post(
        f"/admin/approve/{reservation_id}",
        json={"comment": "Looks good"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "approved successfully" in data["message"]

    res_response = client.get(f"/admin/reservation/{reservation_id}", headers=auth_headers)
    assert res_response.json()["status"] == "approved"
    assert res_response.json()["admin_comment"] == "Looks good"


def test_approve_reservation_without_comment(client, auth_headers):
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response = client.post(f"/admin/approve/{reservation_id}", json={}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_reject_reservation(client, auth_headers):
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response = client.post(
        f"/admin/reject/{reservation_id}",
        json={"reason": "No space available"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "rejected" in data["message"]

    res_response = client.get(f"/admin/reservation/{reservation_id}", headers=auth_headers)
    assert res_response.json()["status"] == "rejected"
    assert res_response.json()["admin_comment"] == "No space available"


def test_approve_non_existent_reservation(client, auth_headers):
    response = client.post("/admin/approve/999", json={}, headers=auth_headers)
    assert response.status_code == 404


def test_reject_non_existent_reservation(client, auth_headers):
    response = client.post("/admin/reject/999", json={"reason": "test"}, headers=auth_headers)
    assert response.status_code == 404


def test_cannot_approve_already_approved_reservation(client, auth_headers):
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response1 = client.post(f"/admin/approve/{reservation_id}", json={}, headers=auth_headers)
    assert response1.status_code == 200

    response2 = client.post(f"/admin/approve/{reservation_id}", json={}, headers=auth_headers)
    assert response2.status_code == 400
    assert "already approved" in response2.json()["detail"]


def test_cannot_reject_already_rejected_reservation(client, auth_headers):
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response1 = client.post(f"/admin/reject/{reservation_id}", json={"reason": "test"}, headers=auth_headers)
    assert response1.status_code == 200

    response2 = client.post(f"/admin/reject/{reservation_id}", json={"reason": "test"}, headers=auth_headers)
    assert response2.status_code == 400
    assert "already rejected" in response2.json()["detail"]


def test_missing_api_key_returns_401(client):
    response = client.get("/admin/pending")
    assert response.status_code == 401

    response = client.post("/admin/approve/1", json={})
    assert response.status_code == 401


def test_invalid_api_key_returns_403(client):
    bad_headers = {"X-API-Key": "invalid-key"}

    response = client.get("/admin/pending", headers=bad_headers)
    assert response.status_code == 403
    assert "Invalid API key" in response.json()["detail"]

"""Tests for Stage 2: Admin REST API endpoints."""

import os
import pytest
from fastapi.testclient import TestClient

from admin.approval_service import app
from db.sql_store import init_db, create_reservation
from config.settings import SQLITE_DB_PATH


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a fresh database for each test."""
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    init_db()
    yield
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def test_health_check(client):
    """Test the root endpoint returns OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_pending_reservations_empty(client):
    """Test listing pending reservations when there are none."""
    response = client.get("/admin/pending")
    assert response.status_code == 200
    assert response.json() == []


def test_list_pending_reservations_with_data(client):
    """Test listing pending reservations."""
    # Create some reservations
    create_reservation("User 1", "AAA-111", "2026-03-10 09:00", "2026-03-10 17:00", "A")
    create_reservation("User 2", "BBB-222", "2026-03-11 10:00", "2026-03-11 18:00")

    response = client.get("/admin/pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["full_name"] == "User 1"
    assert data[1]["full_name"] == "User 2"


def test_get_reservation_details(client):
    """Test getting full details of a reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00", "A"
    )

    response = client.get(f"/admin/reservation/{reservation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == reservation_id
    assert data["full_name"] == "John Doe"
    assert data["status"] == "pending"


def test_get_reservation_details_not_found(client):
    """Test getting a non-existent reservation returns 404."""
    response = client.get("/admin/reservation/999")
    assert response.status_code == 404


def test_approve_reservation(client):
    """Test approving a reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response = client.post(
        f"/admin/approve/{reservation_id}",
        json={"comment": "Looks good"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "approved successfully" in data["message"]

    # Verify the status was updated
    res_response = client.get(f"/admin/reservation/{reservation_id}")
    assert res_response.json()["status"] == "approved"
    assert res_response.json()["admin_comment"] == "Looks good"


def test_approve_reservation_without_comment(client):
    """Test approving without a comment."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response = client.post(f"/admin/approve/{reservation_id}", json={})
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_reject_reservation(client):
    """Test rejecting a reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    response = client.post(
        f"/admin/reject/{reservation_id}",
        json={"reason": "No space available"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "rejected" in data["message"]

    # Verify the status was updated
    res_response = client.get(f"/admin/reservation/{reservation_id}")
    assert res_response.json()["status"] == "rejected"
    assert res_response.json()["admin_comment"] == "No space available"


def test_approve_non_existent_reservation(client):
    """Test approving a non-existent reservation returns 404."""
    response = client.post("/admin/approve/999", json={})
    assert response.status_code == 404


def test_reject_non_existent_reservation(client):
    """Test rejecting a non-existent reservation returns 404."""
    response = client.post("/admin/reject/999", json={"reason": "test"})
    assert response.status_code == 404


def test_cannot_approve_already_approved_reservation(client):
    """Test that you cannot approve an already approved reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    # First approval
    response1 = client.post(f"/admin/approve/{reservation_id}", json={})
    assert response1.status_code == 200

    # Second approval should fail
    response2 = client.post(f"/admin/approve/{reservation_id}", json={})
    assert response2.status_code == 400
    assert "already approved" in response2.json()["detail"]


def test_cannot_reject_already_rejected_reservation(client):
    """Test that you cannot reject an already rejected reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    # First rejection
    response1 = client.post(f"/admin/reject/{reservation_id}", json={"reason": "test"})
    assert response1.status_code == 200

    # Second rejection should fail
    response2 = client.post(f"/admin/reject/{reservation_id}", json={"reason": "test"})
    assert response2.status_code == 400
    assert "already rejected" in response2.json()["detail"]

import pytest
from fastapi.testclient import TestClient

from admin.approval_service import app
from db.sql_store import init_db, create_reservation
from storage.file_writer import get_confirmed_reservations, clear_confirmed_reservations
from config.settings import SQLITE_DB_PATH, ADMIN_API_KEY
import os


@pytest.fixture(autouse=True)
def clean_environment():
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    init_db()

    clear_confirmed_reservations()

    yield

    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    clear_confirmed_reservations()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": ADMIN_API_KEY}


def test_approve_writes_to_file(client, auth_headers):
    reservation_id = create_reservation(
        full_name="Alice Smith",
        license_plate="XYZ-789",
        start_datetime="2026-03-15 10:00",
        end_datetime="2026-03-15 18:00",
        zone_preference="B",
    )

    response = client.post(
        f"/admin/approve/{reservation_id}",
        json={"comment": "VIP customer"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    confirmed = get_confirmed_reservations()
    assert len(confirmed) == 1
    assert confirmed[0]["full_name"] == "Alice Smith"
    assert confirmed[0]["license_plate"] == "XYZ-789"
    assert "2026-03-15 10:00 - 2026-03-15 18:00" in confirmed[0]["period"]
    assert confirmed[0]["approved_at"] is not None


def test_reject_does_not_write_to_file(client, auth_headers):
    reservation_id = create_reservation(
        full_name="Bob Jones",
        license_plate="ABC-456",
        start_datetime="2026-03-16 09:00",
        end_datetime="2026-03-16 17:00",
    )

    response = client.post(
        f"/admin/reject/{reservation_id}",
        json={"reason": "No space available"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    confirmed = get_confirmed_reservations()
    assert len(confirmed) == 0


def test_multiple_approvals_write_to_file(client, auth_headers):
    ids = []
    for i in range(3):
        reservation_id = create_reservation(
            full_name=f"User {i}",
            license_plate=f"PLATE-{i}",
            start_datetime="2026-03-20 09:00",
            end_datetime="2026-03-20 17:00",
        )
        ids.append(reservation_id)

    for rid in ids:
        response = client.post(f"/admin/approve/{rid}", json={}, headers=auth_headers)
        assert response.status_code == 200

    confirmed = get_confirmed_reservations()
    assert len(confirmed) == 3

    names = [c["full_name"] for c in confirmed]
    assert "User 0" in names
    assert "User 1" in names
    assert "User 2" in names


def test_approve_without_zone_preference(client, auth_headers):
    reservation_id = create_reservation(
        full_name="Test User",
        license_plate="TEST-999",
        start_datetime="2026-03-25 08:00",
        end_datetime="2026-03-25 16:00",
        zone_preference=None,
    )

    response = client.post(f"/admin/approve/{reservation_id}", json={}, headers=auth_headers)
    assert response.status_code == 200

    confirmed = get_confirmed_reservations()
    assert len(confirmed) == 1
    assert confirmed[0]["full_name"] == "Test User"

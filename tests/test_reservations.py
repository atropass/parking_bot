"""Tests for Stage 2: Reservation management and approval workflow."""

import os
import pytest

from db.sql_store import (
    init_db,
    create_reservation,
    get_reservation,
    get_pending_reservations,
    update_reservation_status,
    get_connection,
)
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


def test_create_reservation_returns_id():
    """Test that create_reservation returns a valid reservation ID."""
    reservation_id = create_reservation(
        full_name="John Doe",
        license_plate="ABC-123",
        start_datetime="2026-03-10 09:00",
        end_datetime="2026-03-10 17:00",
        zone_preference="A",
    )
    assert reservation_id == 1

    # Create another
    reservation_id2 = create_reservation(
        full_name="Jane Smith",
        license_plate="XYZ-789",
        start_datetime="2026-03-11 10:00",
        end_datetime="2026-03-11 18:00",
    )
    assert reservation_id2 == 2


def test_get_reservation_returns_correct_data():
    """Test that get_reservation retrieves the correct reservation."""
    reservation_id = create_reservation(
        full_name="John Doe",
        license_plate="ABC-123",
        start_datetime="2026-03-10 09:00",
        end_datetime="2026-03-10 17:00",
        zone_preference="A",
    )

    reservation = get_reservation(reservation_id)
    assert reservation is not None
    assert reservation["full_name"] == "John Doe"
    assert reservation["license_plate"] == "ABC-123"
    assert reservation["status"] == "pending"
    assert reservation["zone_preference"] == "A"


def test_get_reservation_returns_none_for_invalid_id():
    """Test that get_reservation returns None for non-existent ID."""
    reservation = get_reservation(999)
    assert reservation is None


def test_get_pending_reservations_filters_correctly():
    """Test that get_pending_reservations only returns pending reservations."""
    # Create 3 reservations
    id1 = create_reservation("User 1", "AAA-111", "2026-03-10 09:00", "2026-03-10 17:00")
    id2 = create_reservation("User 2", "BBB-222", "2026-03-11 09:00", "2026-03-11 17:00")
    id3 = create_reservation("User 3", "CCC-333", "2026-03-12 09:00", "2026-03-12 17:00")

    # Approve one, reject another
    update_reservation_status(id1, "approved", "Looks good")
    update_reservation_status(id3, "rejected", "No space")

    # Only id2 should be pending
    pending = get_pending_reservations()
    assert len(pending) == 1
    assert pending[0]["id"] == id2
    assert pending[0]["full_name"] == "User 2"


def test_update_reservation_status_to_approved():
    """Test approving a reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    success = update_reservation_status(reservation_id, "approved", "All good")
    assert success is True

    reservation = get_reservation(reservation_id)
    assert reservation["status"] == "approved"
    assert reservation["admin_comment"] == "All good"
    assert reservation["reviewed_at"] is not None


def test_update_reservation_status_to_rejected():
    """Test rejecting a reservation."""
    reservation_id = create_reservation(
        "John Doe", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00"
    )

    success = update_reservation_status(reservation_id, "rejected", "No availability")
    assert success is True

    reservation = get_reservation(reservation_id)
    assert reservation["status"] == "rejected"
    assert reservation["admin_comment"] == "No availability"


def test_update_reservation_status_returns_false_for_invalid_id():
    """Test that update returns False for non-existent reservation."""
    success = update_reservation_status(999, "approved")
    assert success is False


def test_reservations_table_exists():
    """Test that the reservations table was created."""
    conn = get_connection()
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reservations'"
    ).fetchall()
    conn.close()

    assert len(tables) == 1
    assert tables[0][0] == "reservations"

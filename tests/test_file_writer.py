import pytest
import threading
from pathlib import Path
from storage.file_writer import (
    write_confirmed_reservation,
    get_confirmed_reservations,
    clear_confirmed_reservations,
    CONFIRMED_RESERVATIONS_FILE,
)


@pytest.fixture(autouse=True)
def clean_file():
    clear_confirmed_reservations()
    yield
    clear_confirmed_reservations()


def test_write_single_reservation():
    write_confirmed_reservation(
        full_name="John Doe",
        license_plate="ABC-123",
        start_datetime="2026-03-10 09:00",
        end_datetime="2026-03-10 17:00",
        approved_at="2026-03-09T15:30:00Z",
    )

    assert Path(CONFIRMED_RESERVATIONS_FILE).exists()

    reservations = get_confirmed_reservations()
    assert len(reservations) == 1
    assert reservations[0]["full_name"] == "John Doe"
    assert reservations[0]["license_plate"] == "ABC-123"
    assert reservations[0]["period"] == "2026-03-10 09:00 - 2026-03-10 17:00"
    assert reservations[0]["approved_at"] == "2026-03-09T15:30:00Z"


def test_write_multiple_reservations():
    write_confirmed_reservation(
        full_name="User One",
        license_plate="AAA-111",
        start_datetime="2026-03-10 09:00",
        end_datetime="2026-03-10 17:00",
        approved_at="2026-03-09T10:00:00Z",
    )

    write_confirmed_reservation(
        full_name="User Two",
        license_plate="BBB-222",
        start_datetime="2026-03-11 10:00",
        end_datetime="2026-03-11 18:00",
        approved_at="2026-03-09T11:00:00Z",
    )

    reservations = get_confirmed_reservations()
    assert len(reservations) == 2
    assert reservations[0]["full_name"] == "User One"
    assert reservations[1]["full_name"] == "User Two"


def test_file_format():
    write_confirmed_reservation(
        full_name="Test User",
        license_plate="XYZ-999",
        start_datetime="2026-03-15 08:00",
        end_datetime="2026-03-15 16:00",
        approved_at="2026-03-14T20:00:00Z",
    )

    with open(CONFIRMED_RESERVATIONS_FILE, "r", encoding="utf-8") as f:
        line = f.read().strip()

    expected = "Test User | XYZ-999 | 2026-03-15 08:00 - 2026-03-15 16:00 | 2026-03-14T20:00:00Z"
    assert line == expected


def test_concurrent_writes():
    def write_reservation(name: str, plate: str):
        write_confirmed_reservation(
            full_name=name,
            license_plate=plate,
            start_datetime="2026-03-10 09:00",
            end_datetime="2026-03-10 17:00",
            approved_at="2026-03-09T12:00:00Z",
        )

    threads = []
    for i in range(10):
        thread = threading.Thread(
            target=write_reservation,
            args=(f"User {i}", f"PLATE-{i:03d}")
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    reservations = get_confirmed_reservations()
    assert len(reservations) == 10

    names = [r["full_name"] for r in reservations]
    assert len(set(names)) == 10


def test_get_reservations_empty_file():
    """Test reading from non-existent file returns empty list."""
    reservations = get_confirmed_reservations()
    assert reservations == []


def test_clear_reservations():
    """Test clearing the reservations file."""
    write_confirmed_reservation(
        full_name="Test",
        license_plate="TEST-123",
        start_datetime="2026-03-10 09:00",
        end_datetime="2026-03-10 17:00",
        approved_at="2026-03-09T12:00:00Z",
    )

    assert Path(CONFIRMED_RESERVATIONS_FILE).exists()

    clear_confirmed_reservations()
    assert not Path(CONFIRMED_RESERVATIONS_FILE).exists()

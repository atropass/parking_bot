import os
import threading
from pathlib import Path
from config.settings import CONFIRMED_RESERVATIONS_FILE as CONFIRMED_FILE


_write_lock = threading.Lock()

CONFIRMED_RESERVATIONS_FILE = CONFIRMED_FILE


def write_confirmed_reservation(
    full_name: str,
    license_plate: str,
    start_datetime: str,
    end_datetime: str,
    approved_at: str,
) -> None:

    file_path = Path(CONFIRMED_RESERVATIONS_FILE)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    period = f"{start_datetime} - {end_datetime}"

    line = f"{full_name} | {license_plate} | {period} | {approved_at}\n"

    with _write_lock:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)


def get_confirmed_reservations() -> list[dict]:
    file_path = Path(CONFIRMED_RESERVATIONS_FILE)

    if not file_path.exists():
        return []

    reservations = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 4:
                reservations.append({
                    "full_name": parts[0],
                    "license_plate": parts[1],
                    "period": parts[2],
                    "approved_at": parts[3],
                })

    return reservations


def clear_confirmed_reservations() -> None:
    file_path = Path(CONFIRMED_RESERVATIONS_FILE)
    if file_path.exists():
        os.remove(file_path)

import sys
from db.sql_store import init_db, create_reservation
from storage.file_writer import get_confirmed_reservations, CONFIRMED_RESERVATIONS_FILE
from config.settings import ADMIN_API_KEY, ADMIN_API_URL
import requests
import time


def create_test_reservations():
    print("=== Creating Test Reservations ===\n")
    init_db()

    reservations = [
        ("Alice Johnson", "ABC-123", "2026-03-10 09:00", "2026-03-10 17:00", "A"),
        ("Bob Smith", "XYZ-789", "2026-03-11 10:00", "2026-03-11 18:00", "B"),
        ("Carol White", "DEF-456", "2026-03-12 08:00", "2026-03-12 16:00", None),
    ]

    ids = []
    for name, plate, start, end, zone in reservations:
        res_id = create_reservation(name, plate, start, end, zone)
        ids.append(res_id)
        zone_text = f"Zone {zone}" if zone else "Any zone"
        print(f"Created reservation #{res_id}: {name} ({plate}) - {zone_text}")

    print(f"\n{len(ids)} reservations created with status='pending'\n")
    return ids


def approve_reservation(reservation_id: int):
    url = f"{ADMIN_API_URL}/admin/approve/{reservation_id}"
    headers = {"X-API-Key": ADMIN_API_KEY}
    try:
        response = requests.post(url, json={"comment": "Approved via demo"}, headers=headers)
        if response.status_code == 200:
            print(f"Approved reservation #{reservation_id}")
            return True
        else:
            print(f"Failed to approve #{reservation_id}: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("\nError: Admin API server is not running!")
        print("Start it with: python demo_stage2.py admin")
        sys.exit(1)


def show_confirmed_reservations():
    print("\n=== Confirmed Reservations (from file) ===\n")

    confirmed = get_confirmed_reservations()

    if not confirmed:
        print("No confirmed reservations yet.")
        return

    print(f"File location: {CONFIRMED_RESERVATIONS_FILE}\n")

    for i, res in enumerate(confirmed, 1):
        print(f"{i}. {res['full_name']} | {res['license_plate']}")
        print(f"   Period: {res['period']}")
        print(f"   Approved: {res['approved_at']}\n")

    print(f"Total confirmed: {len(confirmed)}")


def show_file_contents():
    print("\n=== Raw File Contents ===\n")

    try:
        with open(CONFIRMED_RESERVATIONS_FILE, "r", encoding="utf-8") as f:
            contents = f.read()
            if contents:
                print(contents)
            else:
                print("File is empty.")
    except FileNotFoundError:
        print("File does not exist yet.")


def run_full_demo():
    print("=" * 60)
    print("Stage 3 Demo: File Persistence of Confirmed Reservations")
    print("=" * 60)
    print()

    reservation_ids = create_test_reservations()

    print("Waiting 2 seconds before approvals...\n")
    time.sleep(2)

    print("=== Approving Reservations ===\n")
    for res_id in reservation_ids:
        approve_reservation(res_id)
        time.sleep(0.5)

    print()

    show_confirmed_reservations()

    show_file_contents()

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


def check_reservation_file():
    show_confirmed_reservations()
    show_file_contents()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python demo_stage3.py demo     - Run full demo (requires admin API running)")
        print("  python demo_stage3.py check    - Check current file contents")
        print("  python demo_stage3.py create   - Create test reservations only")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "demo":
        run_full_demo()
    elif command == "check":
        check_reservation_file()
    elif command == "create":
        create_test_reservations()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

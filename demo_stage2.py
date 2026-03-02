import sys
from db.sql_store import init_db, create_reservation, get_reservation, get_pending_reservations
from config.settings import ADMIN_API_PORT, ADMIN_API_HOST


def run_admin_server():
    print(f"Starting Admin API server on http://{ADMIN_API_HOST}:{ADMIN_API_PORT}")
    print(f"Access interactive docs at: http://{ADMIN_API_HOST}:{ADMIN_API_PORT}/docs")
    print(f"Dashboard at: http://{ADMIN_API_HOST}:{ADMIN_API_PORT}/admin/dashboard")
    print("\nAvailable endpoints:")
    print("  GET  /admin/pending          - List pending reservations")
    print("  POST /admin/approve/{id}     - Approve reservation")
    print("  POST /admin/reject/{id}      - Reject reservation")
    print("\nPress Ctrl+C to stop\n")

    import uvicorn
    from admin.approval_service import app
    uvicorn.run(app, host=ADMIN_API_HOST, port=ADMIN_API_PORT)


def simulate_user_reservation():
    print("=== Simulating User Reservation ===\n")

    init_db()

    print("Creating reservation...")
    reservation_id = create_reservation(
        full_name="John Doe",
        license_plate="ABC-123",
        start_datetime="2026-03-10 09:00",
        end_datetime="2026-03-10 17:00",
        zone_preference="A",
    )

    print(f"\n✓ Reservation created successfully!")
    print(f"  Reservation ID: #{reservation_id}")
    print(f"  Name: John Doe")
    print(f"  License Plate: ABC-123")
    print(f"  Period: 2026-03-10 09:00 to 17:00")
    print(f"  Zone: A")
    print(f"  Status: pending")
    print(f"\nThe reservation is waiting for admin approval.")
    print(f"\nTo approve via API:")
    print(f"  curl -X POST http://{ADMIN_API_HOST}:{ADMIN_API_PORT}/admin/approve/{reservation_id} -H 'Content-Type: application/json' -H 'X-API-Key: your_key' -d '{{}}'")
    print(f"\nTo reject via API:")
    print(f"  curl -X POST http://{ADMIN_API_HOST}:{ADMIN_API_PORT}/admin/reject/{reservation_id} -H 'Content-Type: application/json' -H 'X-API-Key: your_key' -d '{{\"reason\": \"No space available\"}}'")
    print(f"\nTo check status:")
    print(f"  python demo_stage2.py check {reservation_id}")


def check_reservation_status(reservation_id: int):
    print(f"=== Checking Reservation #{reservation_id} ===\n")

    init_db()
    reservation = get_reservation(reservation_id)

    if not reservation:
        print(f"Error: Reservation #{reservation_id} not found")
        return

    print(f"Name: {reservation['full_name']}")
    print(f"License Plate: {reservation['license_plate']}")
    print(f"Period: {reservation['start_datetime']} to {reservation['end_datetime']}")
    if reservation['zone_preference']:
        print(f"Zone: {reservation['zone_preference']}")
    print(f"\nStatus: {reservation['status'].upper()}")

    if reservation['status'] == 'pending':
        print("⏳ Waiting for admin approval...")
    elif reservation['status'] == 'approved':
        print("✓ Approved!")
        if reservation['admin_comment']:
            print(f"   Admin comment: {reservation['admin_comment']}")
        print(f"   Reviewed at: {reservation['reviewed_at']}")
    elif reservation['status'] == 'rejected':
        print("✗ Rejected")
        if reservation['admin_comment']:
            print(f"   Reason: {reservation['admin_comment']}")
        print(f"   Reviewed at: {reservation['reviewed_at']}")


def list_all_pending():
    print("=== Pending Reservations ===\n")

    init_db()
    pending = get_pending_reservations()

    if not pending:
        print("No pending reservations.")
        return

    for res in pending:
        print(f"ID #{res['id']}: {res['full_name']} ({res['license_plate']})")
        print(f"  Period: {res['start_datetime']} to {res['end_datetime']}")
        if res['zone_preference']:
            print(f"  Zone: {res['zone_preference']}")
        print(f"  Created: {res['created_at']}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "admin":
        run_admin_server()
    elif command == "user":
        simulate_user_reservation()
    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: python demo_stage2.py check <reservation_id>")
            sys.exit(1)
        reservation_id = int(sys.argv[2])
        check_reservation_status(reservation_id)
    elif command == "pending":
        list_all_pending()
    else:
        print(__doc__)
        sys.exit(1)

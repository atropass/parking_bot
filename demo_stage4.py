import sys
import time
import threading
from db.sql_store import init_db, update_reservation_status, get_pending_reservations
from orchestration.workflow import run_workflow


def simulate_admin_approval(delay_seconds=5):
    print(f"\n[SIMULATED ADMIN] Starting automated approval in {delay_seconds}s...")

    time.sleep(delay_seconds)

    # Get pending reservations
    pending = get_pending_reservations()

    if pending:
        reservation_id = pending[0]["id"]
        print(f"\n[SIMULATED ADMIN] Auto-approving reservation #{reservation_id}...")

        update_reservation_status(
            reservation_id=reservation_id,
            status="approved",
            admin_comment="Auto-approved by simulation",
        )

        print(f"[SIMULATED ADMIN] Reservation #{reservation_id} approved!")
    else:
        print("\n[SIMULATED ADMIN] No pending reservations found")


def demo_auto_approve():
    print("""
   STAGE 4 DEMO: Automatic Approval (Simulated Admin)

   This demo runs the complete workflow with automated
   admin approval for testing purposes.
    """)

    init_db()

    admin_thread = threading.Thread(
        target=simulate_admin_approval,
        args=(8,),
        daemon=True
    )
    admin_thread.start()

    try:
        final_state = run_workflow()

        print("\n" + "="*60)
        print("DEMO COMPLETED")
        print("="*60)
        print(f"Reservation ID: #{final_state.get('reservation_id')}")
        print(f"Admin Decision: {final_state.get('admin_decision', 'N/A').upper()}")
        if final_state.get('error'):
            print(f"Error: {final_state['error']}")
        print("="*60)

    except Exception as e:
        print(f"\nDemo failed: {str(e)}")
        sys.exit(1)


def demo_manual_approve():
    print("""
   STAGE 4 DEMO: Manual Approval

   This demo requires you to approve the reservation
   manually using Admin Agent or API.
    """)

    init_db()

    print("\nMANUAL APPROVAL REQUIRED")
    print("\n1. Keep this terminal running")
    print("2. Open another terminal and run ONE of:")
    print("   • python run_admin_agent.py  (AI-powered)")
    print("   • curl commands (see below)")
    print("\n3. Approve the reservation when workflow starts polling\n")

    input("Press ENTER when ready to start workflow...")

    try:
        final_state = run_workflow()

        print("\n" + "="*60)
        print("DEMO COMPLETED")
        print("="*60)
        if final_state.get('reservation_id'):
            print(f"Reservation ID: #{final_state['reservation_id']}")
        if final_state.get('admin_decision'):
            print(f"Admin Decision: {final_state['admin_decision'].upper()}")
        if final_state.get('error'):
            print(f"Error: {final_state['error']}")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nDemo failed: {str(e)}")
        sys.exit(1)


def show_usage():
    print("""
Usage: python demo_stage4.py [mode]

Modes:
  auto     - Automatic approval (simulated admin) - recommended for testing
  manual   - Manual approval (requires Admin Agent or API)

Examples:
  python demo_stage4.py auto      # Automated demo
  python demo_stage4.py manual    # Manual approval demo

For manual mode, you can approve via:
Admin Agent: python run_admin_agent.py
Admin API:   See README for curl examples
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "auto":
        demo_auto_approve()
    elif mode == "manual":
        demo_manual_approve()
    else:
        print(f"Unknown mode: {mode}")
        show_usage()
        sys.exit(1)

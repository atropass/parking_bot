import os
import sys
import time
import threading

from config.settings import GOOGLE_API_KEY, CHROMA_PERSIST_DIR
from db.sql_store import init_db, update_reservation_status, get_pending_reservations
from db.vector_store import build_vector_store, load_vector_store
from orchestration.workflow import run_workflow


def setup():
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found in .env file.")
        sys.exit(1)

    init_db()

    if not os.path.exists(CHROMA_PERSIST_DIR):
        print("Building vector store (first run)...")
        build_vector_store()
    else:
        load_vector_store()


def simulate_admin_approval():
    """Poll for pending reservations and auto-approve the first one found."""
    print("\n[SIMULATED ADMIN] Watching for pending reservations...")

    for _ in range(120):
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
            return
        time.sleep(1)

    print("\n[SIMULATED ADMIN] Timeout: no pending reservations appeared")


def demo_auto_approve():
    print("""
   STAGE 4 DEMO: Automatic Approval (Simulated Admin)

   Chat with the assistant to make a reservation.
   Once submitted, it will be auto-approved by a background thread.
    """)

    setup()

    admin_thread = threading.Thread(target=simulate_admin_approval, daemon=True)
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

   Chat with the assistant to make a reservation.
   Then approve it from another terminal.
    """)

    setup()

    print("MANUAL APPROVAL REQUIRED")
    print("\n1. Keep this terminal running")
    print("2. Open another terminal and run ONE of:")
    print("   python run_admin_agent.py  (AI-powered)")
    print("   curl commands (see README)")
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

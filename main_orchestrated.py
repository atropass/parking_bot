import sys
from orchestration.workflow import run_workflow
from db.sql_store import init_db


def main():
    print("PARKING RESERVATION SYSTEM - STAGE 4 ORCHESTRATION")
    print("Complete workflow with:")
    print("• User interaction (RAG + LLM)")
    print("• Admin approval (human-in-the-loop)")
    print("• File persistence")
    print("• Automated notifications")

    print("Initializing system...")
    init_db()
    print("Database initialized")
    print("IMPORTANT: Admin API server must be running for approval!")
    print("Run in separate terminal: python demo_stage2.py admin")
    print("Or use Admin Agent: python run_admin_agent.py")
    print("Press ENTER to start the workflow...")
    input()
    try:    
        final_state = run_workflow()

        print("\n" + "="*60)
        print("WORKFLOW SUMMARY")
        print("="*60)
        if final_state.get("reservation_id"):
            print(f"Reservation ID: #{final_state['reservation_id']}")
        if final_state.get("admin_decision"):
            print(f"Admin Decision: {final_state['admin_decision'].upper()}")
        if final_state.get("error"):
            print(f"Error: {final_state['error']}")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nWorkflow failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

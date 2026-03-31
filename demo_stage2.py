"""
Stage 2 Demo: Human-in-the-Loop Parking Reservation System

This demo shows the complete HITL flow:
  1. User submits a reservation through the chatbot agent
  2. The LangGraph flow STOPS (interrupt) and waits for admin approval
  3. Admin approves/rejects via the REST API (FastAPI)
  4. The flow RESUMES and the user receives the admin's decision

Usage:
  python demo_stage2.py              - Run the full automated HITL demo
  python demo_stage2.py admin        - Start only the Admin API server
  python demo_stage2.py pending      - List pending reservations
  python demo_stage2.py check <id>   - Check reservation status
"""

import os
import sys
import time
import logging
import threading

from db.sql_store import init_db, get_reservation, get_pending_reservations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_admin_server():
    logger.info("Starting Admin API server on http://localhost:8000")
    logger.info("Interactive docs at: http://localhost:8000/docs")

    import uvicorn
    from admin.approval_service import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


def run_hitl_demo():
    logger.info("=== Human-in-the-Loop Demo ===")

    from config.settings import GOOGLE_API_KEY, CHROMA_PERSIST_DIR
    from db.vector_store import build_vector_store, load_vector_store
    from agents.rag_chain import build_graph
    from langchain_core.messages import HumanMessage
    from langgraph.types import Command

    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not set in .env")
        sys.exit(1)

    init_db()

    if not os.path.exists(CHROMA_PERSIST_DIR):
        logger.info("Building vector store...")
        build_vector_store()
    else:
        load_vector_store()

    from admin.approval_service import app as admin_app
    import uvicorn

    server_thread = threading.Thread(
        target=lambda: uvicorn.run(admin_app, host="0.0.0.0", port=8000, log_level="warning"),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1)
    logger.info("Admin API server started in background")

    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-hitl"}}

    logger.info("Step 1: User requests a parking reservation")
    user_message = (
        "I want to reserve a parking spot. My name is John Doe, "
        "license plate ABC-123, from 2026-03-10 09:00 to 2026-03-10 17:00, zone A."
    )
    logger.info("User: %s", user_message)

    result = graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config,
    )

    state = graph.get_state(config)
    if not state.next:
        logger.error("Graph did not interrupt. HITL flow not triggered.")
        sys.exit(1)

    interrupt_data = state.tasks[0].interrupts[0].value
    logger.info("Step 2: Flow STOPPED - Human-in-the-Loop interrupt triggered")
    logger.info("Interrupt data: %s", interrupt_data)

    import httpx
    logger.info("Step 3: Admin approves reservation via REST API")
    response = httpx.get("http://localhost:8000/admin/pending")
    pending = response.json()
    if pending:
        res_id = pending[0]["id"]
        approve_response = httpx.post(
            f"http://localhost:8000/admin/approve/{res_id}",
            json={"comment": "Approved by admin"},
        )
        logger.info("Admin API response: %s", approve_response.json())

    logger.info("Step 4: Resuming graph with admin decision")
    result = graph.invoke(
        Command(resume={"status": "approved", "comment": "Approved by admin"}),
        config,
    )

    for msg in reversed(result["messages"]):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            logger.info("Bot response to user: %s", msg.content)
            break

    logger.info("=== Demo complete: Full HITL flow executed successfully ===")


def check_reservation_status(reservation_id: int):
    init_db()
    reservation = get_reservation(reservation_id)

    if not reservation:
        logger.error("Reservation #%d not found", reservation_id)
        return

    logger.info("Reservation #%d:", reservation_id)
    logger.info("  Name: %s", reservation["full_name"])
    logger.info("  License Plate: %s", reservation["license_plate"])
    logger.info("  Period: %s to %s", reservation["start_datetime"], reservation["end_datetime"])
    if reservation["zone_preference"]:
        logger.info("  Zone: %s", reservation["zone_preference"])
    logger.info("  Status: %s", reservation["status"].upper())
    if reservation["admin_comment"]:
        logger.info("  Admin comment: %s", reservation["admin_comment"])


def list_all_pending():
    init_db()
    pending = get_pending_reservations()

    if not pending:
        logger.info("No pending reservations.")
        return

    for res in pending:
        logger.info(
            "  #%d: %s (%s) - %s to %s",
            res["id"], res["full_name"], res["license_plate"],
            res["start_datetime"], res["end_datetime"],
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        run_hitl_demo()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "admin":
        init_db()
        run_admin_server()
    elif command == "check":
        if len(sys.argv) < 3:
            logger.error("Usage: python demo_stage2.py check <reservation_id>")
            sys.exit(1)
        check_reservation_status(int(sys.argv[2]))
    elif command == "pending":
        list_all_pending()
    else:
        print(__doc__)
        sys.exit(1)

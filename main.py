import os
import sys
import re
import time
import logging

from config.settings import GOOGLE_API_KEY, CHROMA_PERSIST_DIR
from db.sql_store import init_db, get_reservation
from db.vector_store import build_vector_store, load_vector_store
from agents.rag_chain import build_graph
from guardrails.pii_filter import redact_pii
from langchain_core.messages import HumanMessage
from langgraph.types import Command

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup():
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not found in .env file.")
        sys.exit(1)

    logger.info("Initializing SQLite database...")
    init_db()

    if not os.path.exists(CHROMA_PERSIST_DIR):
        logger.info("Building vector store (first run)...")
        build_vector_store()
        logger.info("Vector store ready.")
    else:
        load_vector_store()
        logger.info("Vector store loaded from disk.")


def _extract_reservation_id(messages) -> int | None:
    for msg in reversed(messages):
        if hasattr(msg, "name") and msg.name == "submit_reservation":
            match = re.search(r"#(\d+)", str(msg.content))
            if match:
                return int(match.group(1))
    return None


def _wait_for_admin_decision(reservation_id: int, poll_interval: float = 2.0) -> dict:
    logger.info("Waiting for admin decision on reservation #%d...", reservation_id)
    print(f"\nReservation #{reservation_id} submitted. Waiting for admin approval...")
    print(f"  Approve: POST http://localhost:8000/admin/approve/{reservation_id}")
    print(f"  Reject:  POST http://localhost:8000/admin/reject/{reservation_id}")

    while True:
        reservation = get_reservation(reservation_id)
        if reservation and reservation["status"] != "pending":
            logger.info("Admin decision received: %s", reservation["status"])
            return {
                "status": reservation["status"],
                "comment": reservation.get("admin_comment", ""),
            }
        time.sleep(poll_interval)


def _get_response_text(messages) -> str:
    ai_messages = [
        m for m in messages
        if hasattr(m, "type") and m.type == "ai" and m.content
    ]

    if not ai_messages:
        return "I couldn't generate a response."

    content = ai_messages[-1].content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def main():
    setup()

    print("\n--- CityPark Central Parking Assistant ---")
    print("Type your question or 'quit' to exit.\n")

    graph = build_graph()
    config = {"configurable": {"thread_id": "user-session-1"}}

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config,
        )

        state = graph.get_state(config)
        if state.next:
            reservation_id = _extract_reservation_id(result["messages"])
            if reservation_id:
                admin_decision = _wait_for_admin_decision(reservation_id)
                result = graph.invoke(Command(resume=admin_decision), config)

        response = _get_response_text(result["messages"])

        if response:
            response = redact_pii(response)

        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    main()

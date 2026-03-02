import time
from typing import TypedDict, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from config.settings import GOOGLE_API_KEY, LLM_MODEL
from db.sql_store import create_reservation, get_reservation
from storage.file_writer import write_confirmed_reservation
from agents.rag_chain import ParkingReservation


class WorkflowState(TypedDict):
    user_input: str
    reservation_data: dict | None
    reservation_id: int | None
    admin_decision: Literal["approved", "rejected", "pending"] | None
    admin_comment: str | None
    final_message: str | None
    error: str | None


def user_interaction_node(state: WorkflowState) -> WorkflowState:
    print("\n" + "="*60)
    print("STAGE 4 WORKFLOW: User Interaction")
    print("="*60)

    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3,
    )

    structured_llm = llm.with_structured_output(ParkingReservation)

    system_prompt = """You are a parking assistant collecting reservation information.
    Ask the user for these details one by one:
    1. Full name (first and last name)
    2. License plate number
    3. Start date and time (format: YYYY-MM-DD HH:MM)
    4. End date and time (format: YYYY-MM-DD HH:MM)
    5. Preferred zone (A, B, or C - optional)

    Be conversational and friendly. After collecting all information, confirm with the user.
    """

    print("\nStarting conversation with user...\n")

    conversation = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="I want to make a parking reservation"),
        HumanMessage(content="My name is Alice Johnson"),
        HumanMessage(content="License plate is XYZ-789"),
        HumanMessage(content="Start: 2026-03-15 10:00"),
        HumanMessage(content="End: 2026-03-15 18:00"),
        HumanMessage(content="Zone A please"),
    ]

    print("User: I want to make a parking reservation")
    print("Agent: Great! I'll help you with that. What's your full name?")
    print("User: Alice Johnson")
    print("Agent: Thank you! What's your license plate number?")
    print("User: XYZ-789")
    print("Agent: When would you like to start your reservation?")
    print("User: 2026-03-15 10:00")
    print("Agent: And when will you finish?")
    print("User: 2026-03-15 18:00")
    print("Agent: Which zone do you prefer? (A, B, or C)")
    print("User: Zone A please")
    print("\nAll information collected!")

    try:
        reservation_data = structured_llm.invoke(conversation)

        state["reservation_data"] = {
            "full_name": reservation_data.full_name,
            "license_plate": reservation_data.license_plate,
            "start_datetime": reservation_data.start_datetime,
            "end_datetime": reservation_data.end_datetime,
            "zone_preference": reservation_data.zone_preference,
        }

        print(f"\nReservation Details:")
        print(f"   Name: {reservation_data.full_name}")
        print(f"   Plate: {reservation_data.license_plate}")
        print(f"   Period: {reservation_data.start_datetime} to {reservation_data.end_datetime}")
        print(f"   Zone: {reservation_data.zone_preference or 'Any'}")

    except Exception as e:
        state["error"] = f"Failed to extract reservation data: {str(e)}"
        print(f"\nError: {state['error']}")

    return state


def create_reservation_node(state: WorkflowState) -> WorkflowState:
    print("\n" + "="*60)
    print("STAGE 4 WORKFLOW: Creating Reservation")
    print("="*60)

    if state.get("error"):
        return state

    reservation_data = state["reservation_data"]

    try:
        reservation_id = create_reservation(
            full_name=reservation_data["full_name"],
            license_plate=reservation_data["license_plate"],
            start_datetime=reservation_data["start_datetime"],
            end_datetime=reservation_data["end_datetime"],
            zone_preference=reservation_data["zone_preference"],
        )

        state["reservation_id"] = reservation_id
        state["admin_decision"] = "pending"

        print(f"\nReservation created successfully!")
        print(f"   Reservation ID: #{reservation_id}")
        print(f"   Status: pending")
        print(f"\nWaiting for administrator approval...")

    except Exception as e:
        state["error"] = f"Failed to create reservation: {str(e)}"
        print(f"\nError: {state['error']}")

    return state


def admin_approval_node(state: WorkflowState) -> WorkflowState:
    print("\n" + "="*60)
    print("STAGE 4 WORKFLOW: Admin Approval (Polling)")
    print("="*60)

    if state.get("error"):
        return state

    reservation_id = state["reservation_id"]

    print(f"\nPolling for admin decision on reservation #{reservation_id}...")
    print("   (Admin can approve/reject via Admin Agent or API)")
    print("\nTIP: Run this in another terminal:")
    print(f"      python run_admin_agent.py")
    print(f"      Admin: Show me pending reservations")
    print(f"      Admin: Approve reservation {reservation_id}")

    max_attempts = 60  # 60 attempts
    poll_interval = 2  # 2 seconds = 2 minutes total wait time

    for attempt in range(max_attempts):
        try:
            reservation = get_reservation(reservation_id)

            if not reservation:
                state["error"] = f"Reservation #{reservation_id} not found"
                return state

            status = reservation["status"]

            if status == "approved":
                state["admin_decision"] = "approved"
                state["admin_comment"] = reservation.get("admin_comment")
                print(f"\nAPPROVED by admin!")
                if state["admin_comment"]:
                    print(f"   Comment: {state['admin_comment']}")
                break

            elif status == "rejected":
                state["admin_decision"] = "rejected"
                state["admin_comment"] = reservation.get("admin_comment")
                print(f"\nREJECTED by admin")
                if state["admin_comment"]:
                    print(f"   Reason: {state['admin_comment']}")
                break

            else:  # still pending
                if attempt % 5 == 0:
                    print(f"Still waiting... ({attempt * poll_interval}s elapsed)")
                time.sleep(poll_interval)

        except Exception as e:
            state["error"] = f"Polling error: {str(e)}"
            print(f"\nError: {state['error']}")
            return state

    if state["admin_decision"] == "pending":
        state["error"] = "Timeout: Admin did not respond in time"
        print(f"\nTimeout: Admin approval timeout")

    return state


def record_data_node(state: WorkflowState) -> WorkflowState:
    print("\n" + "="*60)
    print("STAGE 4 WORKFLOW: Recording Data")
    print("="*60)

    if state.get("error") or state["admin_decision"] != "approved":
        return state

    reservation_id = state["reservation_id"]

    try:
        reservation = get_reservation(reservation_id)

        write_confirmed_reservation(
            full_name=reservation["full_name"],
            license_plate=reservation["license_plate"],
            start_datetime=reservation["start_datetime"],
            end_datetime=reservation["end_datetime"],
            approved_at=reservation["reviewed_at"],
        )

        print(f"\nReservation recorded to file!")
        print(f"   File: confirmed_reservations/approved.txt")

    except Exception as e:
        print(f"\nWarning: Failed to write to file: {str(e)}")
        print(f"   (Reservation is still approved in database)")

    return state


def notify_user_node(state: WorkflowState) -> WorkflowState:
    print("\n" + "="*60)
    print("STAGE 4 WORKFLOW: User Notification")
    print("="*60)

    if state.get("error"):
        state["final_message"] = f"Error: {state['error']}"
    elif state["admin_decision"] == "approved":
        message = f"""
Congratulations! Your reservation has been APPROVED!

Reservation Details:
- Reservation ID: #{state['reservation_id']}
- Name: {state['reservation_data']['full_name']}
- License Plate: {state['reservation_data']['license_plate']}
- Period: {state['reservation_data']['start_datetime']} to {state['reservation_data']['end_datetime']}
- Zone: {state['reservation_data']['zone_preference'] or 'Any'}

{f"Admin Comment: {state['admin_comment']}" if state['admin_comment'] else ""}

Your reservation has been confirmed and recorded.
See you at the parking facility! 
"""
        state["final_message"] = message
    elif state["admin_decision"] == "rejected":
        message = f"""
Sorry, your reservation has been REJECTED.

Reservation Details:
- Reservation ID: #{state['reservation_id']}
- Name: {state['reservation_data']['full_name']}

Reason: {state['admin_comment'] or 'No reason provided'}

Please contact the facility for more information or try a different time.
"""
        state["final_message"] = message
    else:
        state["final_message"] = "Request timeout. Please contact the facility."

    print(state["final_message"])

    return state


def should_record_data(state: WorkflowState) -> Literal["record_data", "notify_user"]:
    if state.get("error") or state["admin_decision"] != "approved":
        return "notify_user"
    return "record_data"


def build_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    workflow.add_node("user_interaction", user_interaction_node)
    workflow.add_node("create_reservation", create_reservation_node)
    workflow.add_node("admin_approval", admin_approval_node)
    workflow.add_node("record_data", record_data_node)
    workflow.add_node("notify_user", notify_user_node)

    workflow.set_entry_point("user_interaction")

    workflow.add_edge("user_interaction", "create_reservation")
    workflow.add_edge("create_reservation", "admin_approval")

    workflow.add_conditional_edges(
        "admin_approval",
        should_record_data,
        {
            "record_data": "record_data",
            "notify_user": "notify_user",
        }
    )

    workflow.add_edge("record_data", "notify_user")
    workflow.add_edge("notify_user", END)

    return workflow.compile()


def run_workflow(user_input: str = "I want to make a reservation") -> WorkflowState:
    print("\n" + "="*58)
    print("STAGE 4: Complete Parking Reservation Workflow")
    print("="*60)

    workflow = build_workflow()

    initial_state: WorkflowState = {
        "user_input": user_input,
        "reservation_data": None,
        "reservation_id": None,
        "admin_decision": None,
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }

    final_state = workflow.invoke(initial_state)

    print("\n" + "="*60)
    print("WORKFLOW COMPLETED")
    print("="*60)

    return final_state

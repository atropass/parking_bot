import requests
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from config.settings import GOOGLE_API_KEY, LLM_MODEL, ADMIN_API_KEY, ADMIN_API_URL


API_BASE_URL = ADMIN_API_URL


class EmptyInput(BaseModel):
    pass


class ApproveInput(BaseModel):
    reservation_id: int = Field(description="The ID of the reservation to approve")
    comment: str | None = Field(
        default=None,
        description="Optional comment explaining why this was approved"
    )


class RejectInput(BaseModel):
    reservation_id: int = Field(description="The ID of the reservation to reject")
    reason: str = Field(description="Required reason explaining why this was rejected")


@tool(
    description=(
        "Get the list of all pending reservations that need admin review. "
        "Returns reservation details including ID, customer name, license plate, "
        "dates, and zone preference."
    ),
    args_schema=EmptyInput,
)
def get_pending_reservations() -> str:
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/pending",
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        response.raise_for_status()

        pending = response.json()

        if not pending:
            return "No pending reservations at the moment."

        result = f"Found {len(pending)} pending reservation(s):\n\n"
        for res in pending:
            result += f"ID: {res['id']}\n"
            result += f"Name: {res['full_name']}\n"
            result += f"License Plate: {res['license_plate']}\n"
            result += f"Period: {res['start_datetime']} to {res['end_datetime']}\n"
            if res.get('zone_preference'):
                result += f"Preferred Zone: {res['zone_preference']}\n"
            result += f"Created: {res['created_at']}\n"
            result += "-" * 50 + "\n"

        return result
    except requests.exceptions.RequestException as e:
        return f"Error fetching pending reservations: {str(e)}"


@tool(
    description=(
        "Approve a reservation by ID. This will update the reservation status to 'approved' "
        "and write it to the confirmed reservations file. You can optionally provide a comment."
    ),
    args_schema=ApproveInput,
)
def approve_reservation(reservation_id: int, comment: str | None = None) -> str:
    try:
        payload = {}
        if comment:
            payload["comment"] = comment

        response = requests.post(
            f"{API_BASE_URL}/admin/approve/{reservation_id}",
            json=payload,
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        response.raise_for_status()

        result = response.json()
        return f"Success: {result['message']}"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Error: Reservation {reservation_id} not found."
        elif e.response.status_code == 400:
            return f"Error: Reservation {reservation_id} has already been processed."
        else:
            return f"Error approving reservation: {e.response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Admin API: {str(e)}"


@tool(
    description=(
        "Reject a reservation by ID. This will update the reservation status to 'rejected'. "
        "You must provide a reason for the rejection."
    ),
    args_schema=RejectInput,
)
def reject_reservation(reservation_id: int, reason: str) -> str:
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/reject/{reservation_id}",
            json={"reason": reason},
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        response.raise_for_status()

        result = response.json()
        return f"Success: {result['message']}"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Error: Reservation {reservation_id} not found."
        elif e.response.status_code == 400:
            return f"Error: Reservation {reservation_id} has already been processed."
        else:
            return f"Error rejecting reservation: {e.response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Admin API: {str(e)}"


ADMIN_SYSTEM_PROMPT = """You are an administrative assistant for the CityPark Central parking facility.

Your role is to help the administrator review and process pending reservations.

Available actions:
- Use get_pending_reservations to see all reservations awaiting approval
- Use approve_reservation to approve a reservation (optionally with a comment)
- Use reject_reservation to reject a reservation (must provide a reason)

Guidelines:
- Always show the administrator the pending reservations first
- Be helpful and professional
- When approving or rejecting, confirm the action was successful
- If there are errors, explain them clearly to the administrator
"""

TOOLS = [
    get_pending_reservations,
    approve_reservation,
    reject_reservation,
]


def build_admin_agent():
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
    )

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=SystemMessage(content=ADMIN_SYSTEM_PROMPT),
    )
    return agent


def run_admin_cli():
    print("=" * 60)
    print("Parking Admin Agent - Reservation Review System")
    print("=" * 60)
    print()
    print("This agent helps you review and process pending reservations.")
    print("Type 'exit' or 'quit' to stop.")
    print()

    agent = build_admin_agent()

    while True:
        try:
            user_input = input("\nAdmin: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye!")
                break

            result = agent.invoke({"messages": [HumanMessage(content=user_input)]})

            ai_messages = [msg for msg in result["messages"] if hasattr(msg, "content")]
            if ai_messages:
                response = ai_messages[-1].content

                if isinstance(response, list):
                    response = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in response
                    )

                print(f"\nAgent: {response}")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    run_admin_cli()

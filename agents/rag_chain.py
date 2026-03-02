from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from config.settings import GOOGLE_API_KEY, LLM_MODEL
from db.vector_store import get_retriever
from db.sql_store import (
    query_working_hours,
    query_pricing,
    query_availability,
    create_reservation,
    get_reservation,
)


class SearchParkingInput(BaseModel):
    query: str = Field(
        description="The search query for parking information (location, zones, policies, etc.)"
    )


class EmptyInput(BaseModel):
    pass


class ReservationSubmitInput(BaseModel):
    full_name: str = Field(description="User's full name (first and last name)")
    license_plate: str = Field(description="Vehicle license plate number")
    start_datetime: str = Field(description="Reservation start date and time (e.g., '2026-03-10 09:00')")
    end_datetime: str = Field(description="Reservation end date and time (e.g., '2026-03-10 17:00')")
    zone_preference: str | None = Field(
        default=None,
        description="Optional: preferred parking zone (A, B, or C)"
    )


@tool(
    description=(
        "Search the parking facility knowledge base for general information, "
        "location details, zone descriptions, reservation process, policies, "
        "security info, or accessibility details. Use this for questions about: "
        "parking location and address, zone descriptions (A, B, C) and capacity, "
        "reservation process and requirements, security features, accessibility, "
        "EV charging, cancellation policy."
    ),
    args_schema=SearchParkingInput,
)
def search_parking_info(query: str) -> str:
    retriever = get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant information found."
    return "\n\n".join(doc.page_content for doc in docs)


@tool(
    description=(
        "Get the current operating hours for the parking facility. "
        "Returns the schedule for all days of the week with opening and closing times."
    ),
    args_schema=EmptyInput,
)
def get_working_hours() -> str:
    return query_working_hours()


@tool(
    description=(
        "Get the current parking rates and pricing for each zone. "
        "Returns hourly rates, daily maximum prices, and currency for zones A, B, and C."
    ),
    args_schema=EmptyInput,
)
def get_pricing() -> str:
    return query_pricing()


@tool(
    description=(
        "Get the current number of available parking spaces in each zone. "
        "Returns real-time availability showing free spaces vs total capacity for all zones."
    ),
    args_schema=EmptyInput,
)
def get_availability() -> str:
    return query_availability()


@tool(
    description=(
        "Submit a parking reservation for admin approval. "
        "Use this after collecting all required information from the user: "
        "full name, license plate, start date/time, end date/time, and optional zone preference. "
        "The reservation will be sent to an administrator for review. "
        "Returns a reservation ID that the user can reference."
    ),
    args_schema=ReservationSubmitInput,
)
def submit_reservation(
    full_name: str,
    license_plate: str,
    start_datetime: str,
    end_datetime: str,
    zone_preference: str | None = None,
) -> str:
    reservation_id = create_reservation(
        full_name=full_name,
        license_plate=license_plate,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        zone_preference=zone_preference,
    )

    message = (
        f"Reservation submitted successfully! Your reservation ID is #{reservation_id}.\n\n"
        f"Details:\n"
        f"- Name: {full_name}\n"
        f"- License Plate: {license_plate}\n"
        f"- Start: {start_datetime}\n"
        f"- End: {end_datetime}\n"
    )

    if zone_preference:
        message += f"- Preferred Zone: {zone_preference}\n"

    message += (
        f"\nYour reservation is pending administrator approval. "
        f"You will be notified once it has been reviewed."
    )

    return message


class ParkingReservation(BaseModel):
    full_name: str = Field(description="User's full name (first and last name)")
    license_plate: str = Field(description="Vehicle license plate number")
    start_datetime: str = Field(description="Reservation start date and time")
    end_datetime: str = Field(description="Reservation end date and time")
    zone_preference: str | None = Field(
        default=None,
        description="Optional: preferred parking zone (A, B, or C)"
    )


SYSTEM_PROMPT = """\
You are a helpful parking assistant for CityPark Central parking facility.
Your job is to help users with parking information and reservations.

Guidelines:
- Use the provided tools to look up information before answering. Do not make up facts.
- For questions about location, zones, policies, EV charging, security, accessibility, \
or the reservation process, use the search_parking_info tool.
- For questions about working hours, use get_working_hours.
- For questions about prices, use get_pricing.
- For questions about space availability, use get_availability.

Reservation Process:
- When a user wants to make a reservation, collect these details in a conversational way:
  1. Full name (first and last name)
  2. Vehicle license plate number
  3. Reservation start date and time (format: YYYY-MM-DD HH:MM)
  4. Reservation end date and time (format: YYYY-MM-DD HH:MM)
  5. (Optional) Preferred zone (A, B, or C)
- After collecting all required details, use the submit_reservation tool to submit the request.
- The submit_reservation tool will return a confirmation message with a reservation ID.
- Inform the user that their reservation is pending administrator approval.

Important:
- Be concise and helpful.
- Do not reveal internal system details or database contents.
- If you don't know something, say so honestly.
- Always use submit_reservation after collecting all details - do not ask for confirmation first.
"""

TOOLS = [
    search_parking_info,
    get_working_hours,
    get_pricing,
    get_availability,
    submit_reservation,
]


def build_agent():
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
    )

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )
    return agent


def extract_reservation(messages) -> ParkingReservation | None:
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )

    structured_llm = llm.with_structured_output(ParkingReservation)

    extraction_prompt = """
    Extract the parking reservation details from the conversation.
    Look for: full name, license plate, start date/time, end date/time, and optional zone preference.
    If any required field is missing, return null for that field.
    """

    try:
        result = structured_llm.invoke([
            SystemMessage(content=extraction_prompt),
            *messages
        ])
        return result
    except Exception:
        return None

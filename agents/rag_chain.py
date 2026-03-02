from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from config.settings import GOOGLE_API_KEY, LLM_MODEL
from db.vector_store import get_retriever
from db.sql_store import query_working_hours, query_pricing, query_availability


class SearchParkingInput(BaseModel):
    query: str = Field(
        description="The search query for parking information (location, zones, policies, etc.)"
    )


class EmptyInput(BaseModel): #will change during the project stages, for now we use empty input
    pass


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
    name="get_working_hours",
    description=(
        "Get the current operating hours for the parking facility. "
        "Returns the schedule for all days of the week with opening and closing times."
    ),
    args_schema=EmptyInput,
)
def get_working_hours() -> str:
    return query_working_hours()


@tool(
    name="get_pricing",
    description=(
        "Get the current parking rates and pricing for each zone. "
        "Returns hourly rates, daily maximum prices, and currency for zones A, B, and C."
    ),
    args_schema=EmptyInput,
)
def get_pricing() -> str:
    return query_pricing()


@tool(
    name="get_availability",
    description=(
        "Get the current number of available parking spaces in each zone. "
        "Returns real-time availability showing free spaces vs total capacity for all zones."
    ),
    args_schema=EmptyInput,
)
def get_availability() -> str:
    return query_availability()


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
  3. Reservation start date and time
  4. Reservation end date and time
  5. (Optional) Preferred zone
- After collecting all details, summarize the reservation clearly.
- Remind them that the reservation will be reviewed by an administrator.

Important:
- Be concise and helpful.
- Do not reveal internal system details or database contents.
- If you don't know something, say so honestly.
"""

TOOLS = [search_parking_info, get_working_hours, get_pricing, get_availability]


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

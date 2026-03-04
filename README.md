# Parking Reservation Chatbot - Complete System (Stages 1-4)

An intelligent end-to-end parking reservation system featuring Retrieval-Augmented Generation (RAG), human-in-the-loop approval workflow, file-based persistence, and full LangGraph orchestration.

## Project Status

**Stage 1 (Complete):** RAG-based chatbot with information retrieval 
**Stage 2 (Complete):** Human-in-the-loop reservation approval system 
**Stage 3 (Complete):** File persistence & security 
**Stage 4 (Complete):** Full LangGraph workflow orchestration 

## Features

### Stage 1: RAG Chatbot

- Retrieval-Augmented Generation using ChromaDB for static data
- Dynamic data queries via SQLite for pricing, hours, and availability
- Guardrails using Microsoft Presidio for PII protection
- LangGraph agent with tool-calling capabilities
- Structured data collection using Pydantic models

### Stage 2: Human-in-the-Loop

- REST API for administrator reservation approval
- Reservation lifecycle management (pending/approved/rejected)
- FastAPI service with interactive documentation
- Database persistence for reservation tracking
- Integration with Stage 1 chatbot via new tool

### Stage 3: File Persistence & Security

- Thread-safe file writing for confirmed reservations
- Text file format: `Name | Plate | Period | Approval Time`
- Automatic file persistence on approval
- **API Key Authentication** - Secure admin endpoints
- **Second Agent (Admin Agent)** - LangChain-based conversational interface for administrators
- Admin agent with natural language processing for reservation management

### Stage 4: LangGraph Orchestration

- **Complete workflow integration** - All stages unified in single pipeline
- **LangGraph StateGraph** - State machine for workflow management
- **Real interactive RAG agent** - Same agent from Stage 1 used in the workflow
- **4 orchestrated nodes:**
  - User Interaction (interactive chat with RAG agent, reservation submitted via tool)
  - Admin Approval (polling mechanism)
  - Data Recording (file persistence)
  - User Notification (final status)
- **Conditional routing** - Approved → file recording, Rejected → skip
- **Polling mechanism** - Waits for admin decision without blocking
- **Error handling** - Graceful degradation at each step
- **Automated demo mode** - Simulated admin for testing

## Architecture

### Data Flow

```
User (CLI)
    ↓
LangGraph Agent (Gemini 2.5 Flash)
    ↓
Tool Selection:
    ├─ search_parking_info → ChromaDB (RAG retrieval)
    ├─ get_working_hours → SQLite (dynamic data)
    ├─ get_pricing → SQLite
    ├─ get_availability → SQLite
    └─ submit_reservation → SQLite (new in Stage 2)
            ↓
    Reservation saved (status='pending')
            ↓
    Admin API (FastAPI server)
            ↓
    Admin approval/rejection (via API or Admin Agent)
            ↓
    Database updated (status='approved'/'rejected')
            ↓
    (Stage 3) Write to file if approved
            ↓
    confirmed_reservations/approved.txt

Admin (CLI) - Stage 3
    ↓
Admin Agent (Gemini 2.5 Flash) - Second Agent
    ↓
Tools with API Key Authentication:
    ├─ get_pending_reservations → Admin API (secured)
    ├─ approve_reservation → Admin API (secured)
    └─ reject_reservation → Admin API (secured)
```

### Stage 4: Orchestrated Workflow

```
START (main_orchestrated.py)
    ↓
┌─────────────────────────────────────────────┐
│  Node 1: User Interaction                   │
│  • Interactive chat with RAG agent          │
│  • Agent collects data conversationally     │
│  • Agent calls submit_reservation tool      │
│  • Reservation created in DB automatically  │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Node 2: Admin Approval (Polling)           │
│  • Poll database every 2 seconds            │
│  • Wait for admin decision via:             │
│    - Admin Agent (run_admin_agent.py)      │
│    - Admin API (curl/Swagger)               │
│  • Max wait: 2 minutes                       │
└─────────────────────────────────────────────┘
    ↓
   [CONDITIONAL EDGE]
    ↓                    ↓
 APPROVED            REJECTED
    ↓                    ↓
┌──────────────┐   ┌──────────────┐
│ Node 3:      │   │ Skip to      │
│ Record Data  │   │ Notification │
│ • Write to   │   └──────────────┘
│   file       │        ↓
└──────────────┘        ↓
    ↓                   ↓
    └───────────────────┘
            ↓
┌─────────────────────────────────────────────┐
│  Node 4: Notify User                        │
│  • Display final status message             │
│  • Include reservation details              │
│  • Show admin comments                       │
└─────────────────────────────────────────────┘
    ↓
   END
```

### Human-in-the-Loop Workflow

```
1. User provides reservation details to chatbot
2. Agent collects: name, plate, start/end times, zone
3. Agent calls submit_reservation tool
4. Reservation saved to SQLite with status='pending'
5. Admin accesses REST API to view pending reservations
6. Admin approves or rejects via POST endpoints
7. Database updated with admin decision and timestamp
8. (Stage 4) User notified of approval status
```

## Technology Stack

- **LLM:** Google Gemini 2.5 Flash (via LangChain)
- **Embeddings:** Gemini Embedding 001
- **Vector Database:** ChromaDB (persistent, local storage)
- **SQL Database:** SQLite (hours, pricing, availability, reservations)
- **Agent Framework:** LangGraph (ReAct agent pattern) - 2 agents (User + Admin)
- **Admin API:** FastAPI with Pydantic validation + API Key authentication
- **Security:** API Key authentication (X-API-Key header)
- **PII Protection:** Microsoft Presidio (spaCy-based NLP)
- **File Storage:** Thread-safe text file persistence (Stage 3)
- **Testing:** pytest with 50 test cases

## Project Structure

```
parking_bot/
├── config/
│   └── settings.py          # Configuration (models, paths, RAG parameters)
├── data/
│   └── parking_info.txt     # Source document for vector embeddings
├── db/
│   ├── sql_store.py         # SQLite operations (Stage 1 + Stage 2)
│   └── vector_store.py      # ChromaDB operations
├── agents/
│   ├── rag_chain.py         # User agent (LangGraph + 5 tools)
│   └── admin_agent.py       # NEW: Admin agent (Stage 3 - Second Agent)
├── admin/                   # Stage 2
│   ├── __init__.py
│   └── approval_service.py  # FastAPI admin REST API with API Key auth
├── storage/                 # NEW: Stage 3
│   ├── __init__.py
│   └── file_writer.py       # Thread-safe file persistence
├── orchestration/           # NEW: Stage 4
│   ├── __init__.py
│   └── workflow.py          # LangGraph workflow orchestration
├── guardrails/
│   └── pii_filter.py        # PII detection and redaction
├── confirmed_reservations/  # NEW: Stage 3 (created at runtime)
│   └── approved.txt         # Confirmed reservations file
├── tests/                   # 50 test cases
│   ├── test_agents.py
│   ├── test_guardrails.py
│   ├── test_sql_store.py
│   ├── test_vector_store.py
│   ├── test_reservations.py       # Stage 2
│   ├── test_admin_api.py          # Stage 2 + security tests
│   ├── test_file_writer.py        # NEW: Stage 3
│   ├── test_stage3_integration.py # NEW: Stage 3
│   └── test_workflow.py           # NEW: Stage 4
├── main.py                  # CLI chatbot entry point (User agent)
├── run_admin_agent.py      # NEW: Stage 3 - Admin agent CLI
├── main_orchestrated.py    # NEW: Stage 4 - Orchestrated workflow
├── demo_stage2.py          # Stage 2 demo script
├── demo_stage3.py          # NEW: Stage 3 demo script
└── demo_stage4.py          # NEW: Stage 4 demo script
```

## Installation

### Prerequisites

- Python 3.13+
- Google Gemini API key

### Setup

1. Clone and navigate to project:

```bash
git clone <repository-url>
cd parking_bot
```

1. Create virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Download spaCy language model for Presidio:

```bash
python -m spacy download en_core_web_lg
```

1. Configure environment:

```bash
# Create .env file with API keys
cat > .env << EOF
GOOGLE_API_KEY=your_gemini_api_key_here
ADMIN_API_KEY=your_secure_admin_key_here
EOF
```

**Important:** Change `ADMIN_API_KEY` to a strong random key in production.

## Usage

### Running the Chatbot (Stage 1)

```bash
python main.py
```

On first run, the system initializes databases and builds the vector store (takes ~10 seconds).

**Example interactions:**

```
You: Where is the parking located?
Assistant: The parking facility is located at 42 Main Street...

You: What are the prices?
Assistant: Zone A: USD 5.00/hour (daily max: USD 35.00)...

You: I want to make a reservation
Assistant: Sure! What's your full name?
You: John Doe
Assistant: Great! What's your license plate number?
You: ABC-123
Assistant: When would you like to start?
You: 2026-03-10 09:00
Assistant: And when will you end?
You: 2026-03-10 17:00
Assistant: Reservation submitted successfully! Your reservation ID is #1...
```

### Running the Admin Service (Stage 2)

**Terminal 1: Start Admin API**

```bash
python demo_stage2.py admin
```

The FastAPI server starts on `http://localhost:8000`. Access interactive documentation at `http://localhost:8000/docs`.

**Terminal 2: Simulate User Reservation**

```bash
python demo_stage2.py user
```

Creates a test reservation with ID #1 and status 'pending'.

**Terminal 3: Admin Approval**

View pending reservations:

```bash
curl http://localhost:8000/admin/pending \
  -H "X-API-Key: your_admin_key_here"
```

Approve a reservation:

```bash
curl -X POST http://localhost:8000/admin/approve/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_admin_key_here" \
  -d '{"comment": "Approved"}'
```

Reject a reservation:

```bash
curl -X POST http://localhost:8000/admin/reject/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_admin_key_here" \
  -d '{"reason": "No space available"}'
```

**Note:** All admin endpoints require `X-API-Key` header for authentication.

Check reservation status:

```bash
python demo_stage2.py check 1
```

### Using Swagger UI

Open browser: `http://localhost:8000/docs`

Interactive API documentation allows testing all endpoints:

- `GET /admin/pending` - List pending reservations
- `GET /admin/reservation/{id}` - Get reservation details
- `POST /admin/approve/{id}` - Approve reservation
- `POST /admin/reject/{id}` - Reject reservation

**Security Note:** Swagger UI will prompt for API Key. Use the value from your `.env` file.

### Running Admin Agent (Stage 3 - Second Agent)

The Admin Agent provides a conversational interface for administrators using natural language.

**Start the Admin Agent:**

```bash
python run_admin_agent.py
```

**Example interactions:**

```
Admin: Show me all pending reservations
Agent: Found 3 pending reservations:
       ID: 1
       Name: Alice Johnson
       License Plate: ABC-123
       Period: 2026-03-10 09:00 to 2026-03-10 17:00
       Preferred Zone: A
       Created: 2026-03-09T10:00:00Z
       ...

Admin: Approve reservation 1 because VIP customer
Agent: Success: Reservation 1 approved successfully

Admin: Reject reservation 2 - no space available
Agent: Success: Reservation 2 rejected: no space available
```

**Features:**
- Natural language understanding
- Automatic API key authentication
- Error handling and validation
- Conversational feedback

**Type 'exit' or 'quit' to stop the agent.**

### Running Stage 3 Demo (File Persistence)

Stage 3 automatically writes approved reservations to `confirmed_reservations/approved.txt`.

**Demo workflow (requires Admin API running):**

```bash
# Terminal 1: Start Admin API
python demo_stage2.py admin

# Terminal 2: Run full Stage 3 demo
python demo_stage3.py demo
```

This will:
1. Create 3 test reservations
2. Approve them via API
3. Display confirmed reservations from file
4. Show raw file contents

**Other commands:**

```bash
# Check current file contents
python demo_stage3.py check

# Create test reservations only
python demo_stage3.py create
```

**File format:**

Each approved reservation is appended to `confirmed_reservations/approved.txt`:

```
Alice Johnson | ABC-123 | 2026-03-10 09:00 - 2026-03-10 17:00 | 2026-03-09T15:30:00Z
Bob Smith | XYZ-789 | 2026-03-11 10:00 - 2026-03-11 18:00 | 2026-03-09T16:00:00Z
```

Format: `Name | License Plate | Reservation Period | Approval Time`

### Running Stage 4 Workflow (Complete Orchestration)

Stage 4 provides the **complete end-to-end workflow** orchestrating all previous stages.

**Option 1: Automated Demo (Recommended for testing)**

This mode simulates admin approval automatically:

```bash
python demo_stage4.py auto
```

**What happens:**
1. You chat with the RAG agent interactively to make a reservation
2. Agent calls `submit_reservation` tool, creating a pending record in the DB
3. Background thread detects the pending reservation and auto-approves it
4. Workflow records to file and notifies you of approval

**Option 2: Manual Approval (Production-like)**

This mode requires real admin interaction:

```bash
# Terminal 1: Run orchestrated workflow
python demo_stage4.py manual

# Terminal 2 (when prompted): Use Admin Agent
python run_admin_agent.py
# Then: "Show pending reservations"
# Then: "Approve reservation 1"
```

**Option 3: Direct Orchestration (For development)**

Use the main orchestration script directly:

```bash
python main_orchestrated.py
```

This provides the full experience with interactive prompts and detailed logging of each workflow node.

**Workflow Features:**
- Automatic state management across nodes
- Conditional routing based on admin decision
- Error handling and graceful degradation
- Real-time polling for admin approval
- Complete notification system

## Agent Tools

The LangGraph agent has access to five tools:

**search_parking_info(query: str)**

- Retrieves information from ChromaDB vector store
- Semantic similarity search with top-k=3 retrieval
- Handles: location, zones, policies, EV charging, security, accessibility

**get_working_hours()**

- Queries SQLite for operating schedule
- Returns hours for all days of the week

**get_pricing()**

- Queries SQLite for current rates
- Returns hourly and daily maximum pricing by zone

**get_availability()**

- Queries SQLite for real-time space counts
- Returns available vs. total spaces per zone

**submit_reservation(...) (Stage 2)**

- Accepts: full_name, license_plate, start_datetime, end_datetime, zone_preference
- Saves reservation to SQLite with status='pending'
- Returns reservation ID and confirmation message
- Triggers human-in-the-loop approval workflow

All tools use explicit Pydantic schemas for input validation.

## Database Schema

### Stage 1 Tables

**working_hours**

```sql
CREATE TABLE working_hours (
    id INTEGER PRIMARY KEY,
    day_of_week TEXT NOT NULL,
    open_time TEXT NOT NULL,
    close_time TEXT NOT NULL
)
```

**pricing**

```sql
CREATE TABLE pricing (
    id INTEGER PRIMARY KEY,
    zone TEXT NOT NULL,
    rate_per_hour REAL NOT NULL,
    daily_max REAL NOT NULL,
    currency TEXT DEFAULT 'USD'
)
```

**availability**

```sql
CREATE TABLE availability (
    id INTEGER PRIMARY KEY,
    zone TEXT NOT NULL,
    total_spaces INTEGER NOT NULL,
    occupied_spaces INTEGER NOT NULL
)
```

### Stage 2 Table

**reservations**

```sql
CREATE TABLE reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    license_plate TEXT NOT NULL,
    start_datetime TEXT NOT NULL,
    end_datetime TEXT NOT NULL,
    zone_preference TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    admin_comment TEXT
)
```

**Status values:** 'pending', 'approved', 'rejected'

**ChromaDB Collection:** `parking_static`

- 20+ chunks from parking_info.txt
- 3072-dimensional embeddings from Gemini
- Persistent storage at `db/chroma_store/`

## Admin REST API

### Endpoints

**GET /**
Health check endpoint. Returns service status.

**GET /admin/pending**
List all reservations with status='pending', ordered by creation time.

**GET /admin/reservation/{id}**
Get full details of a specific reservation including status, timestamps, and admin comments.

**POST /admin/approve/{id}**
Approve a pending reservation. Optional request body:

```json
{"comment": "Approved for VIP customer"}
```

**POST /admin/reject/{id}**
Reject a pending reservation. Required request body:

```json
{"reason": "No space available"}
```

### Response Models

All endpoints use Pydantic models for validation:

**ReservationResponse** - Full reservation details
**PendingReservationResponse** - Simplified pending list
**StatusResponse** - Success/error messages

### Error Handling

- **401 Unauthorized**: Missing API key
- **403 Forbidden**: Invalid API key
- **404 Not Found**: Reservation not found
- **400 Bad Request**: Reservation already processed (cannot approve/reject twice)
- **500 Internal Server Error**: Database operation failed

### Security

**API Key Authentication (Stage 3):**

All admin endpoints (`/admin/*`) require authentication via `X-API-Key` header.

- API key is configured in `.env` file as `ADMIN_API_KEY`
- Default key: `default-admin-key-change-in-production`
- **Change this in production!**

The Admin Agent automatically uses the API key from configuration.

## Testing

Run the full test suite:

```bash
pytest tests/ -v
```

**Test Coverage (50 tests):**

**test_agents.py (2 tests)**

- Pydantic schema validation
- Tool configuration

**test_guardrails.py (2 tests)**

- PII detection (credit cards, IBAN)
- PII redaction

**test_sql_store.py (2 tests)**

- Database initialization
- Query operations

**test_vector_store.py (1 test)**

- Vector retrieval accuracy

**test_reservations.py (8 tests)** - Stage 2

- Reservation creation
- Status queries
- Pending filtering
- Status updates
- Edge cases

**test_admin_api.py (14 tests)** - Stage 2 + Security

- API endpoint functionality
- Approval/rejection workflows
- Error handling (404, 400, 401, 403)
- Idempotency checks
- API key authentication tests (Stage 3)

**test_file_writer.py (6 tests)** - Stage 3

- Single and multiple reservation writes
- File format validation
- Thread-safe concurrent writes
- File read operations
- Cleanup operations

**test_stage3_integration.py (4 tests)** - Stage 3

- Approval writes to file
- Rejection does not write
- Multiple approvals
- Edge cases (no zone preference)

**test_workflow.py (11 tests)** - Stage 4

- User interaction node (data extraction)
- Reservation creation node
- Admin approval node (approved/rejected scenarios)
- Data recording node (with conditional execution)
- User notification node (all outcomes)
- Conditional edge logic
- Full workflow integration with mocked polling

All tests use isolated fixtures to prevent cross-contamination.

## Configuration

Key settings in `config/settings.py`:

```python
LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"
RETRIEVAL_TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
```

**RAG tuning:**

- Adjust `CHUNK_SIZE` to balance retrieval granularity vs. context preservation
- Increase `CHUNK_OVERLAP` if answers lose context at boundaries
- Modify `RETRIEVAL_TOP_K` if answers lack detail (try 4-5)

## RAG Implementation

### Document Processing

1. Load `parking_info.txt` as single document
2. Split using RecursiveCharacterTextSplitter:
  - Chunk size: 500 characters
  - Overlap: 50 characters
  - Split priority: paragraphs > sentences > words
3. Embed each chunk via Gemini (3072-dimensional vectors)
4. Store in ChromaDB with persistent storage

### Retrieval

1. Embed user query using same model
2. Compute cosine similarity against stored vectors
3. Return top-3 most similar chunks
4. Concatenate chunks as context for LLM

**Why chunking:** LLMs have token limits. Smaller chunks improve precision.
**Why overlap:** Prevents information loss at chunk boundaries.

## Guardrails

Microsoft Presidio detects and redacts sensitive information before responses are shown to users.

**Detected Entity Types:**

- CREDIT_CARD, IBAN_CODE, CRYPTO
- US_SSN, US_PASSPORT, US_DRIVER_LICENSE
- US_BANK_NUMBER, MEDICAL_LICENSE
- IP_ADDRESS

**Not blocked:** Email addresses and phone numbers (legitimate facility contact info)

Presidio combines regex, ML models, and context-aware rules for accurate detection with low false positives.

## Development Notes

### Adding New Tools

1. Define Pydantic input schema in `agents/rag_chain.py`
2. Create tool function with `@tool` decorator
3. Add explicit `description` parameter (what LLM reads)
4. Add to `TOOLS` list
5. Update `SYSTEM_PROMPT` with usage instructions

### Extending Database

1. Add table creation in `db/sql_store.py` `init_db()`
2. Create query/mutation functions
3. Add tests in `tests/test_sql_store.py`

### Adding API Endpoints

1. Define Pydantic request/response models in `admin/approval_service.py`
2. Implement endpoint with proper error handling
3. Add tests in `tests/test_admin_api.py`

## Known Limitations

- CLI interface only (no web UI yet)
- Admin must manually poll API or use Admin Agent for pending reservations
- Workflow uses polling for admin approval (WebSocket push notifications could enhance UX)
- SQLite availability data is static (production needs real-time updates)
- Basic API Key authentication (production should use OAuth2/JWT)
- File storage is append-only (no archival or rotation mechanism)
- Admin Agent runs locally (no multi-user support)

## Stage 3 Implementation Details

### File Writer Module

**Location:** `storage/file_writer.py`

**Thread Safety:**
Uses `threading.Lock()` to prevent concurrent write conflicts when multiple admins approve reservations simultaneously.

**File Operations:**
- **write_confirmed_reservation()** - Appends approved reservation to file
- **get_confirmed_reservations()** - Reads all confirmed reservations
- **clear_confirmed_reservations()** - Clears file (testing only)

**Integration Point:**
The `admin/approval_service.py` approve endpoint automatically calls `write_confirmed_reservation()` after successful database update.

**Error Handling:**
File write errors are caught and logged but do not fail the approval (database is source of truth).

### API Key Authentication

**Location:** `admin/approval_service.py`

**Implementation:**
- FastAPI `APIKeyHeader` security scheme
- Header name: `X-API-Key`
- Validates against `ADMIN_API_KEY` from environment
- Returns **401** if key is missing, **403** if key is invalid

**Usage:**
```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

All admin endpoints use `api_key: str = Security(verify_api_key)` dependency.

### Admin Agent (Second Agent)

**Location:** `agents/admin_agent.py`

**Architecture:**
- LangChain `ChatGoogleGenerativeAI` with Gemini 2.5 Flash
- LangGraph `create_react_agent` pattern
- 3 tools with API authentication

**Tools:**
1. **get_pending_reservations()** - Fetches pending list from API
2. **approve_reservation(id, comment)** - Approves with optional comment
3. **reject_reservation(id, reason)** - Rejects with required reason

All tools automatically include `X-API-Key` header when calling Admin API.

**Natural Language Processing:**
The agent understands commands like:
- "Show me pending reservations"
- "Approve reservation 1 because VIP"
- "Reject 2 - no space"

**Error Handling:**
- API connection errors
- Invalid reservation IDs
- Already processed reservations

## Stage 4 Implementation Details

### LangGraph Workflow Orchestration

**Location:** `orchestration/workflow.py`

**Architecture:**
- LangGraph `StateGraph` for state machine orchestration
- TypedDict-based state management across all nodes
- Conditional routing based on admin approval decisions
- Polling mechanism for human-in-the-loop integration

### Workflow State

```python
class WorkflowState(TypedDict):
    user_input: str
    reservation_data: dict | None
    reservation_id: int | None
    admin_decision: Literal["approved", "rejected", "pending"] | None
    admin_comment: str | None
    final_message: str | None
    error: str | None
```

State is immutable and passed between nodes, with each node returning updates.

### Workflow Nodes

**1. user_interaction_node**
- Launches the full RAG agent from Stage 1 (`build_agent()`)
- User chats interactively via `input()` — can ask questions, get info, then make a reservation
- When the agent calls `submit_reservation` tool, the reservation is created in the DB
- The node detects the reservation ID from the tool response and populates workflow state
- PII redaction is applied to all agent responses

**2. admin_approval_node**
- Implements polling mechanism (2-second intervals, 2-minute timeout)
- Checks database for status changes (approved/rejected)
- Displays admin comment when decision is made
- Gracefully handles timeouts

**3. record_data_node**
- Only executes if admin_decision == 'approved'
- Writes to file using Stage 3 file_writer module
- Non-blocking: file write errors don't fail workflow

**4. notify_user_node**
- Terminal node that displays final message
- Handles three outcomes: approved, rejected, error
- Provides complete reservation details and next steps

### Conditional Routing

```python
def should_record_data(state: WorkflowState) -> Literal["record_data", "notify_user"]:
    if state.get("error") or state["admin_decision"] != "approved":
        return "notify_user"
    return "record_data"
```

**Graph Structure:**
```
START → user_interaction → admin_approval
       → [if approved] → record_data → notify_user → END
       → [if rejected/error] → notify_user → END
```

### Error Handling

- Errors propagate through state without crashing workflow
- Each node checks for existing errors before executing
- Failed file writes log warnings but don't block notifications
- Timeout handling with user-friendly messages

### Integration Points

**With Stage 1 (RAG):**
- Uses `build_agent()` from agents/rag_chain.py directly in the workflow
- Same interactive RAG agent with all 5 tools available during conversation

**With Stage 2 (Admin API):**
- Polls database updated by Admin API or Admin Agent
- Compatible with existing approval mechanisms

**With Stage 3 (File Persistence):**
- Calls `write_confirmed_reservation()` for approved reservations
- Maintains same file format and thread safety

### Testing

**Location:** `tests/test_workflow.py`

**Coverage:** 11 test cases covering:
- Individual node functionality
- Error handling scenarios
- Conditional edge logic
- Full workflow integration
- Mocked time.sleep for fast tests

### Demo Modes

**Automated Mode:**
- You chat with the RAG agent interactively to make a reservation
- Background thread polls for pending reservations and auto-approves
- No second terminal needed for admin

**Manual Mode:**
- Requires real Admin Agent or API interaction
- Production-like experience
- Tests full integration with existing systems


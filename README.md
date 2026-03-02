# Parking Reservation Chatbot - Stages 1 & 2

An intelligent chatbot for CityPark Central parking facility using Retrieval-Augmented Generation (RAG) for information retrieval and human-in-the-loop workflow for reservation approval.

## Project Status

**Stage 1 (Complete):** RAG-based chatbot with information retrieval
**Stage 2 (Complete):** Human-in-the-loop reservation approval system
**Stage 3 (Planned):** MCP server for confirmed reservation persistence
**Stage 4 (Planned):** Full LangGraph orchestration

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
    Admin approval/rejection
            ↓
    Database updated (status='approved'/'rejected')
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
- **Agent Framework:** LangGraph (ReAct agent pattern)
- **Admin API:** FastAPI with Pydantic validation
- **PII Protection:** Microsoft Presidio (spaCy-based NLP)
- **Testing:** pytest with 27 test cases

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
│   └── rag_chain.py         # LangGraph agent + 5 tools
├── admin/                   # NEW: Stage 2
│   ├── __init__.py
│   └── approval_service.py  # FastAPI admin REST API
├── guardrails/
│   └── pii_filter.py        # PII detection and redaction
├── tests/                   # 27 test cases
│   ├── test_agents.py
│   ├── test_guardrails.py
│   ├── test_sql_store.py
│   ├── test_vector_store.py
│   ├── test_reservations.py     # NEW: Stage 2
│   └── test_admin_api.py        # NEW: Stage 2
├── main.py                  # CLI chatbot entry point
└── demo_stage2.py          # NEW: Stage 2 demo script
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
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

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
curl http://localhost:8000/admin/pending
```

Approve a reservation:

```bash
curl -X POST http://localhost:8000/admin/approve/1 \
  -H "Content-Type: application/json" \
  -d '{"comment": "Approved"}'
```

Reject a reservation:

```bash
curl -X POST http://localhost:8000/admin/reject/1 \
  -H "Content-Type: application/json" \
  -d '{"reason": "No space available"}'
```

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

- 404: Reservation not found
- 400: Reservation already processed (cannot approve/reject twice)
- 500: Database operation failed

## Testing

Run the full test suite:

```bash
pytest tests/ -v
```

**Test Coverage (27 tests):**

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

**test_admin_api.py (12 tests)** - Stage 2

- API endpoint functionality
- Approval/rejection workflows
- Error handling (404, 400)
- Idempotency checks

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
- Admin must manually poll API for pending reservations
- No real-time notifications (Stage 4 will add WebSocket or polling)
- SQLite availability data is static (production needs real-time updates)
- No authentication on admin API (add OAuth2 for production)

## Future Stages

**Stage 3: MCP Server Integration**

- Write confirmed reservations to persistent storage
- File format: `Name | Plate | Period | Approval Time`
- MCP server or function calling for data persistence

**Stage 4: LangGraph Orchestration**

- Full state machine pipeline integration
- Nodes for user interaction, admin approval, data recording
- Automatic status notifications to users
- Complete workflow with error handling and retries


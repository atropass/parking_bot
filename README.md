# Parking Reservation Chatbot - Stage 1

An intelligent chatbot for CityPark Central parking facility that uses Retrieval-Augmented Generation (RAG) to provide information and handle parking reservations.

## Overview

This is Stage 1 of a 4-stage project implementing a full-featured parking assistant with human-in-the-loop reservation approval. The current implementation focuses on:

- RAG-based information retrieval using ChromaDB for static data
- Dynamic data queries via SQLite for pricing, hours, and availability
- Guardrails using Microsoft Presidio for PII protection
- LangGraph agent with tool-calling capabilities
- Structured data collection using Pydantic models

## Architecture

The system uses a hybrid data approach:

**Static Data (ChromaDB):**
- Parking location and address
- Zone descriptions and policies
- Reservation process details
- Security features, accessibility, EV charging info

**Dynamic Data (SQLite):**
- Working hours schedule
- Real-time pricing by zone
- Current space availability

This separation allows updating frequently-changing data without re-indexing the entire knowledge base.

### RAG Pipeline

```
User Query
    ↓
Gemini Embedding (models/gemini-embedding-001)
    ↓
ChromaDB Similarity Search (top-k=3)
    ↓
Retrieved Chunks + Original Query
    ↓
LangGraph Agent (gemini-2.5-flash)
    ↓
Tool Selection & Execution
    ↓
Response Generation
    ↓
PII Redaction (Presidio)
    ↓
User Response
```

## Project Structure

```
parking_bot/
├── config/
│   └── settings.py          # Configuration (models, paths, RAG parameters)
├── data/
│   └── parking_info.txt     # Source document for vector embeddings
├── db/
│   ├── sql_store.py         # SQLite operations (hours, pricing, availability)
│   └── vector_store.py      # ChromaDB operations (embeddings, retrieval)
├── agents/
│   └── rag_chain.py         # LangGraph agent + tools + Pydantic schemas
├── guardrails/
│   └── pii_filter.py        # PII detection and redaction using Presidio
├── tests/                   # Test suite (7 tests covering core functionality)
└── main.py                  # CLI entry point
```

## Technology Stack

- **LLM:** Google Gemini 2.5 Flash (via LangChain)
- **Embeddings:** Gemini Embedding 001
- **Vector Database:** ChromaDB (persistent, local storage)
- **SQL Database:** SQLite (in-memory seeding on startup)
- **Agent Framework:** LangGraph (ReAct agent pattern)
- **PII Protection:** Microsoft Presidio (spaCy-based NLP)
- **Schema Validation:** Pydantic v2

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd parking_bot
```

2. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download spaCy language model for Presidio:
```bash
python -m spacy download en_core_web_lg
```

5. Configure environment:
```bash
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

## Usage

Run the chatbot:
```bash
python main.py
```

On first run, the system will:
- Initialize SQLite database with seed data
- Build vector store by embedding parking_info.txt (takes ~10 seconds)
- Start the interactive CLI

Example interactions:
```
You: Where is the parking located?
Assistant: The parking facility is located at 42 Main Street...

You: What are the prices?
Assistant: Zone A: USD 5.00/hour (daily max: USD 35.00)...

You: How many spaces are available?
Assistant: Zone A: 63 spaces available out of 150...
```

Type `quit` or press Ctrl+C to exit.

## Agent Tools

The LangGraph agent has access to four tools:

**search_parking_info(query: str)**
- Retrieves information from ChromaDB vector store
- Handles questions about location, zones, policies, EV charging, security
- Uses semantic similarity search with top-k=3 retrieval

**get_working_hours()**
- Queries SQLite for operating schedule
- Returns hours for all days of the week

**get_pricing()**
- Queries SQLite for current rates
- Returns hourly and daily maximum pricing by zone

**get_availability()**
- Queries SQLite for real-time space counts
- Returns available vs. total spaces per zone

All tools use explicit Pydantic schemas for input validation and include descriptions that the LLM uses for tool selection.

## RAG Implementation Details

**Document Processing:**
1. Load parking_info.txt as single document
2. Split using RecursiveCharacterTextSplitter:
   - Chunk size: 500 characters
   - Overlap: 50 characters (preserves context at boundaries)
   - Split priority: paragraphs > sentences > words
3. Embed each chunk via Gemini (3072-dimensional vectors)
4. Store in ChromaDB with persistent storage

**Retrieval:**
1. Embed user query using same model
2. Compute cosine similarity against all stored vectors
3. Return top-3 most similar chunks
4. Concatenate chunks and pass to LLM as context

**Why Chunking:**
- LLMs have token limits; full document may exceed context window
- Smaller chunks improve retrieval precision
- Overlap prevents information loss at chunk boundaries

## Guardrails

The system uses Microsoft Presidio to prevent leakage of sensitive information:

**Detected Entity Types:**
- Financial: CREDIT_CARD, IBAN_CODE, CRYPTO, US_BANK_NUMBER
- Identity: US_SSN, US_PASSPORT, US_DRIVER_LICENSE, MEDICAL_LICENSE
- Technical: IP_ADDRESS

**Not Blocked:**
- Email addresses and phone numbers (legitimate contact info for parking facility)
- Names and dates (needed for reservation context)

Presidio combines regex patterns, ML models, and context-aware rules for accurate detection. All responses are filtered before display.

## Pydantic Models

**Tool Input Schemas:**
```python
class SearchParkingInput(BaseModel):
    query: str = Field(description="...")

class EmptyInput(BaseModel):
    pass  # For tools with no parameters
```

**Structured Output:**
```python
class ParkingReservation(BaseModel):
    full_name: str
    license_plate: str
    start_datetime: str
    end_datetime: str
    zone_preference: str | None = None
```

Used with `with_structured_output()` to extract reservation details from conversation history.

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

**Test Coverage:**
- `test_agents.py`: Pydantic schema validation, tool configuration
- `test_guardrails.py`: PII detection and redaction
- `test_sql_store.py`: Database initialization and queries
- `test_vector_store.py`: Vector retrieval accuracy

All tests use isolated fixtures to prevent cross-contamination. Vector store tests create temporary ChromaDB instances.

## Configuration

Key settings in `config/settings.py`:

```python
LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"
RETRIEVAL_TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
```

Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` to balance retrieval granularity vs. context preservation. Increase `RETRIEVAL_TOP_K` if answers lack sufficient detail.

## Database Schema

**SQLite Tables:**

`working_hours`: (day_of_week, open_time, close_time)
`pricing`: (zone, rate_per_hour, daily_max, currency)
`availability`: (zone, total_spaces, occupied_spaces)

All tables are created and seeded on first run via `init_db()`. Data persists at `db/parking.db`.

**ChromaDB:**

Collection: `parking_static`
- Documents: 20+ chunks from parking_info.txt
- Embeddings: 3072-dimensional vectors
- Metadata: source file path
- Storage: `db/chroma_store/` (SQLite + vector index)

## Known Limitations

- Single-user CLI only (no web interface)
- No actual reservation persistence (Stage 3 will add MCP server)
- No admin approval workflow (Stage 2 will add human-in-the-loop)
- SQLite availability data is static (would need real-time updates in production)

## Future Stages

**Stage 2:** Human-in-the-Loop Agent
- Administrator approval workflow via email/messenger/REST API
- Integration between user-facing agent and admin agent

**Stage 3:** MCP Server Integration
- Write confirmed reservations to persistent storage
- File format: Name | Plate | Period | Approval Time

**Stage 4:** LangGraph Orchestration
- Full pipeline integration using LangGraph state machines
- Nodes for user interaction, admin approval, data recording
- Complete workflow testing

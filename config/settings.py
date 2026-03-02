import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "db", "chroma_store")
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "parking.db")

CHROMA_COLLECTION_NAME = "parking_static"

RETRIEVAL_TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

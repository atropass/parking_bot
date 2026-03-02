import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "default-admin-key-change-in-production")
ADMIN_API_HOST = os.getenv("ADMIN_API_HOST", "localhost")
ADMIN_API_PORT = int(os.getenv("ADMIN_API_PORT", "8000"))
ADMIN_API_URL = f"http://{ADMIN_API_HOST}:{ADMIN_API_PORT}"

LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "db", "chroma_store")
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "parking.db")
CONFIRMED_RESERVATIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "confirmed_reservations", "approved.txt")

CHROMA_COLLECTION_NAME = "parking_static"

RETRIEVAL_TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

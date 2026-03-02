import os
import shutil
import pytest

from config.settings import CHROMA_PERSIST_DIR
from db.vector_store import build_vector_store, get_retriever


@pytest.fixture(scope="module")
def vector_store():
    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)
    store = build_vector_store()
    yield store
    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)


def test_retriever_returns_results(vector_store):
    retriever = get_retriever()
    docs = retriever.invoke("Where is the parking located?")
    assert len(docs) > 0
    combined = " ".join(d.page_content for d in docs)
    assert "Main Street" in combined

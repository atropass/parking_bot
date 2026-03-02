import os
import pytest

from db.sql_store import init_db, query_pricing, get_connection
from config.settings import SQLITE_DB_PATH


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    init_db()
    yield
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)


def test_init_creates_tables():
    conn = get_connection()
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()

    table_names = {row[0] for row in tables}
    assert "working_hours" in table_names
    assert "pricing" in table_names
    assert "availability" in table_names


def test_pricing_has_all_zones():
    result = query_pricing()
    assert "Zone A" in result
    assert "Zone B" in result
    assert "Zone C" in result

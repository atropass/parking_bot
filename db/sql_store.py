import sqlite3
from config.settings import SQLITE_DB_PATH


def get_connection():
    return sqlite3.connect(SQLITE_DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS working_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week TEXT NOT NULL,
            open_time TEXT NOT NULL,
            close_time TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pricing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT NOT NULL,
            rate_per_hour REAL NOT NULL,
            daily_max REAL NOT NULL,
            currency TEXT DEFAULT 'USD'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT NOT NULL,
            total_spaces INTEGER NOT NULL,
            occupied_spaces INTEGER NOT NULL
        )
    """)

    if cursor.execute("SELECT COUNT(*) FROM working_hours").fetchone()[0] == 0:
        hours_data = [
            ("Monday", "06:00", "23:00"),
            ("Tuesday", "06:00", "23:00"),
            ("Wednesday", "06:00", "23:00"),
            ("Thursday", "06:00", "23:00"),
            ("Friday", "06:00", "00:00"),
            ("Saturday", "07:00", "00:00"),
            ("Sunday", "07:00", "22:00"),
        ]
        cursor.executemany(
            "INSERT INTO working_hours (day_of_week, open_time, close_time) VALUES (?, ?, ?)",
            hours_data,
        )

    if cursor.execute("SELECT COUNT(*) FROM pricing").fetchone()[0] == 0:
        pricing_data = [
            ("A", 5.00, 35.00, "USD"),
            ("B", 3.50, 25.00, "USD"),
            ("C", 7.00, 45.00, "USD"),
        ]
        cursor.executemany(
            "INSERT INTO pricing (zone, rate_per_hour, daily_max, currency) VALUES (?, ?, ?, ?)",
            pricing_data,
        )

    if cursor.execute("SELECT COUNT(*) FROM availability").fetchone()[0] == 0:
        availability_data = [
            ("A", 150, 87),
            ("B", 120, 45),
            ("C", 80, 22),
        ]
        cursor.executemany(
            "INSERT INTO availability (zone, total_spaces, occupied_spaces) VALUES (?, ?, ?)",
            availability_data,
        )

    conn.commit()
    conn.close()


def query_working_hours():
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT day_of_week, open_time, close_time FROM working_hours ORDER BY id"
    ).fetchall()
    conn.close()

    lines = []
    for day, open_t, close_t in rows:
        lines.append(f"{day}: {open_t} - {close_t}")
    return "\n".join(lines)


def query_pricing():
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT zone, rate_per_hour, daily_max, currency FROM pricing ORDER BY zone"
    ).fetchall()
    conn.close()

    lines = []
    for zone, rate, daily, currency in rows:
        lines.append(
            f"Zone {zone}: {currency} {rate:.2f}/hour (daily max: {currency} {daily:.2f})"
        )
    return "\n".join(lines)


def query_availability():
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT zone, total_spaces, occupied_spaces FROM availability ORDER BY zone"
    ).fetchall()
    conn.close()

    lines = []
    for zone, total, occupied in rows:
        free = total - occupied
        lines.append(f"Zone {zone}: {free} spaces available out of {total}")
    return "\n".join(lines)

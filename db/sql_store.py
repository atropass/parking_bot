import sqlite3
from datetime import datetime, timezone
from typing import Optional
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
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


def create_reservation(
    full_name: str,
    license_plate: str,
    start_datetime: str,
    end_datetime: str,
    zone_preference: Optional[str] = None,
) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    created_at = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT INTO reservations
        (full_name, license_plate, start_datetime, end_datetime, zone_preference, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """,
        (full_name, license_plate, start_datetime, end_datetime, zone_preference, created_at),
    )

    reservation_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return reservation_id


def get_reservation(reservation_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        """
        SELECT id, full_name, license_plate, start_datetime, end_datetime,
               zone_preference, status, created_at, reviewed_at, admin_comment
        FROM reservations
        WHERE id = ?
        """,
        (reservation_id,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "full_name": row[1],
        "license_plate": row[2],
        "start_datetime": row[3],
        "end_datetime": row[4],
        "zone_preference": row[5],
        "status": row[6],
        "created_at": row[7],
        "reviewed_at": row[8],
        "admin_comment": row[9],
    }


def get_pending_reservations() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT id, full_name, license_plate, start_datetime, end_datetime,
               zone_preference, created_at
        FROM reservations
        WHERE status = 'pending'
        ORDER BY created_at ASC
        """
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "full_name": row[1],
            "license_plate": row[2],
            "start_datetime": row[3],
            "end_datetime": row[4],
            "zone_preference": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def update_reservation_status(
    reservation_id: int,
    status: str,
    admin_comment: Optional[str] = None,
) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    reviewed_at = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        UPDATE reservations
        SET status = ?, reviewed_at = ?, admin_comment = ?
        WHERE id = ?
        """,
        (status, reviewed_at, admin_comment, reservation_id),
    )

    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return updated

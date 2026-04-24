import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(
    "/tmp" if os.path.exists("/tmp") else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    ),
    "prices.db",
)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fisherman_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT UNIQUE,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                coastal_location TEXT,
                district TEXT,
                preferred_species TEXT,
                fishing_zone TEXT,
                boat_type TEXT,
                registration_number TEXT,
                created_at TEXT,
                last_seen TEXT
            )
        """)
        conn.commit()


init_db()


def _row_to_dict(row) -> dict:
    return dict(row) if row else None


def create_profile(
    name: str,
    phone: str,
    coastal_location: str = None,
    district: str = None,
    preferred_species: str = None,
    fishing_zone: str = None,
    boat_type: str = None,
    registration_number: str = None,
) -> dict:
    now = datetime.now().isoformat()
    profile_id = str(int(datetime.now().timestamp() * 1000))

    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM fisherman_profiles WHERE phone = ?", (phone,)
        ).fetchone()
        if existing:
            raise ValueError(f"Profile with phone {phone} already exists")

        conn.execute(
            """
            INSERT INTO fisherman_profiles
              (profile_id, name, phone, coastal_location, district,
               preferred_species, fishing_zone, boat_type,
               registration_number, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id, name, phone, coastal_location, district,
                preferred_species, fishing_zone, boat_type,
                registration_number, now, now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM fisherman_profiles WHERE phone = ?", (phone,)
        ).fetchone()
        return _row_to_dict(row)


def get_profile(phone: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM fisherman_profiles WHERE phone = ?", (phone,)
        ).fetchone()
        return _row_to_dict(row)


def update_location(phone: str, coastal_location: str, district: str) -> dict:
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE fisherman_profiles
            SET coastal_location = ?, district = ?, last_seen = ?
            WHERE phone = ?
            """,
            (coastal_location, district, now, phone),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM fisherman_profiles WHERE phone = ?", (phone,)
        ).fetchone()
        return _row_to_dict(row)


def update_last_seen(phone: str) -> None:
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "UPDATE fisherman_profiles SET last_seen = ? WHERE phone = ?",
            (now, phone),
        )
        conn.commit()


def get_all_profiles() -> list:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM fisherman_profiles").fetchall()
        return [_row_to_dict(r) for r in rows]

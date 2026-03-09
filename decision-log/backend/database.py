"""
Database initialisation and connection helpers.

Using plain sqlite3 (Python stdlib) — no ORM dependency.
The schema is defined here as the single source of truth.

DESIGN NOTE: We use WAL mode for better concurrent read performance.
Each request creates and closes its own connection (per Flask request lifecycle).
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH: Path | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL CHECK(length(trim(title))      >= 5),
    context        TEXT    NOT NULL CHECK(length(trim(context))    >= 10),
    decision_text  TEXT    NOT NULL CHECK(length(trim(decision_text)) >= 10),
    consequences   TEXT,
    status         TEXT    NOT NULL DEFAULT 'proposed'
                           CHECK(status IN ('proposed','accepted','rejected','superseded')),
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);
"""


def configure(db_path: str) -> None:
    """Call once at app startup to set the DB file path."""
    global _DB_PATH
    _DB_PATH = Path(db_path)


def get_connection() -> sqlite3.Connection:
    """
    Open a new sqlite3 connection with row_factory set to Row
    so columns are accessible by name.
    Callers are responsible for closing (or use as a context manager).
    """
    if _DB_PATH is None:
        raise RuntimeError("Database not configured. Call database.configure(path) first.")
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they do not exist. Idempotent."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database initialised at %s", _DB_PATH)

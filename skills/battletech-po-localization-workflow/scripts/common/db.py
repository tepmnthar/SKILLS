"""Shared sqlite helpers for the BattleTech PO workflow."""
import os
import sqlite3

DB_NAME = "localization.sqlite"

SCHEMA_TRANSLATIONS = """
CREATE TABLE IF NOT EXISTS translations (
    Key TEXT PRIMARY KEY,
    SourceLocation TEXT,
    msgid TEXT NOT NULL,
    msgstr TEXT,
    isTranslated INTEGER NOT NULL DEFAULT 0,
    hasPlaceholder INTEGER NOT NULL DEFAULT 0
)
"""
SCHEMA_TRANSLATIONS_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_translations_msgid ON translations(msgid)"
)
SCHEMA_TERMINOLOGY = """
CREATE TABLE IF NOT EXISTS terminology (
    term TEXT PRIMARY KEY,
    translation TEXT
)
"""


def db_path(workspace: str, db_name: str = DB_NAME) -> str:
    return os.path.join(workspace, db_name)


def open_db(workspace: str, db_name: str = DB_NAME) -> sqlite3.Connection:
    os.makedirs(workspace, exist_ok=True)
    conn = sqlite3.connect(db_path(workspace, db_name))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(SCHEMA_TRANSLATIONS)
    conn.execute(SCHEMA_TRANSLATIONS_INDEX)
    conn.execute(SCHEMA_TERMINOLOGY)
    conn.commit()

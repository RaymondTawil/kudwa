from __future__ import annotations
import sqlite3
from sqlite3 import Connection
from app.obs.traces import init_traces

from . import db as _self  # type: ignore

# SQL schema for initializing the database tables and indexes
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    period_start TEXT,
    period_end TEXT,
    month_key TEXT,
    source TEXT,
    account TEXT,
    category TEXT,
    kind TEXT,
    amount REAL
);
CREATE INDEX IF NOT EXISTS ix_facts_month ON facts(month_key);
CREATE INDEX IF NOT EXISTS ix_facts_src ON facts(source);


CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY,
    period_end TEXT,
    source TEXT,
    revenue REAL,
    cogs REAL,
    gross_profit REAL,
    expenses REAL,
    net_profit REAL,
    UNIQUE(period_end, source)
);


CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conv_id TEXT,
    role TEXT,
    content TEXT,
    ts TEXT
);
"""

# Singleton connection object
_CON: Connection | None = None


def get_con(db_path: str) -> Connection:
    """
    Get a singleton SQLite connection to the database at db_path.
    Sets row_factory to sqlite3.Row for dict-like access.
    """
    global _CON
    if _CON is None:
        _CON = sqlite3.connect(db_path, check_same_thread=False)
        _CON.row_factory = sqlite3.Row
    return _CON


def init_db(con: Connection):
    """
    Initialize the database schema and tracing tables.
    """
    with con:
        con.executescript(SCHEMA_SQL)
    init_traces(con)
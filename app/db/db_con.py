# app/deps/db.py
from __future__ import annotations
from sqlite3 import Connection
from fastapi import Request
from app.db.db import get_con
from app.config import settings

def db_conn(request: Request) -> Connection:
    """
    FastAPI dependency that returns a SQLite connection.
    Uses app.state.con if present; otherwise initializes and caches it.
    """
    con = getattr(request.app.state, "con", None)
    if con is None:
        con = get_con(settings.db_path)
        request.app.state.con = con
    return con

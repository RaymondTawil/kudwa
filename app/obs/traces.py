from __future__ import annotations
import json
from sqlite3 import Connection
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# SQL schema for the ai_traces table and indexes
SCHEMA_TRACE = """
CREATE TABLE IF NOT EXISTS ai_traces (
    id INTEGER PRIMARY KEY,
    ts TEXT,
    conversation_id TEXT,
    question TEXT,
    answer TEXT,
    model TEXT,
    tokens_prompt INTEGER,
    tokens_completion INTEGER,
    latency_ms REAL,
    tool_calls TEXT -- JSON array
);
CREATE INDEX IF NOT EXISTS ix_ai_traces_ts ON ai_traces(ts);
CREATE INDEX IF NOT EXISTS ix_ai_traces_conv ON ai_traces(conversation_id);
"""

class TraceIn(BaseModel):
    ts: str
    conversation_id: Optional[str]
    question: str
    answer: str
    model: Optional[str]
    tokens_prompt: Optional[int]
    tokens_completion: Optional[int]
    latency_ms: float
    tool_calls: List[Dict[str, Any]] = []


def init_traces(con: Connection):
    """
    Initialize the ai_traces table and indexes in the database.
    """
    with con:
        con.executescript(SCHEMA_TRACE)


def trace_log(con: Connection, t: TraceIn):
    """
    Insert a trace record into the ai_traces table.
    """
    with con:
        con.execute(
            """
            INSERT INTO ai_traces(ts, conversation_id, question, answer, model, tokens_prompt, tokens_completion, latency_ms, tool_calls)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (t.ts, t.conversation_id, t.question, t.answer, t.model, t.tokens_prompt or 0, t.tokens_completion or 0, t.latency_ms, json.dumps(t.tool_calls))
        )


def traces_recent(con: Connection, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent trace records, up to the specified limit.
    """
    cur = con.execute("SELECT * FROM ai_traces ORDER BY ts DESC LIMIT ?", (limit,))
    out = []
    for r in cur.fetchall():
        d = dict(r)
        try:
            d["tool_calls"] = json.loads(d.get("tool_calls") or "[]")
        except Exception:
            d["tool_calls"] = []
        out.append(d)
    return out


def traces_by_conv(con: Connection, conv_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all trace records for a given conversation ID.
    """
    cur = con.execute("SELECT * FROM ai_traces WHERE conversation_id=? ORDER BY ts DESC", (conv_id,))
    out = []
    for r in cur.fetchall():
        d = dict(r)
        try:
            d["tool_calls"] = json.loads(d.get("tool_calls") or "[]")
        except Exception:
            d["tool_calls"] = []
        out.append(d)
    return out
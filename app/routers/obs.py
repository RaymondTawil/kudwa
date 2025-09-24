from __future__ import annotations
from sqlite3 import Connection
from fastapi import APIRouter, Depends
from app.db.db_con import db_conn
from app.obs.traces import traces_recent, traces_by_conv

# Create a FastAPI router for observability endpoints
router = APIRouter(prefix="/api/v1/obs", tags=["observability"])


@router.get("/traces/recent")
def recent_traces(con: Connection = Depends(db_conn), limit: int = 50):
    """
    API endpoint to get the most recent trace records.
    Returns a list of trace rows, up to the specified limit.
    """
    return {"rows": traces_recent(con, limit)}


@router.get("/traces/by_conv")
def by_conv(conversation_id: str, con: Connection = Depends(db_conn)):
    """
    API endpoint to get all trace records for a given conversation ID.
    Returns a list of trace rows for the specified conversation.
    """
    return {"rows": traces_by_conv(con, conversation_id)}
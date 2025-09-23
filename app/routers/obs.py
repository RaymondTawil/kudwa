from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlite3 import Connection
from app.db.db_con import db_conn
from app.obs.traces import traces_recent, traces_by_conv


router = APIRouter(prefix="/api/v1/obs", tags=["observability"])


@router.get("/traces/recent")
def recent_traces(con: Connection = Depends(db_conn), limit: int = 50):
    return {"rows": traces_recent(con, limit)}


@router.get("/traces/by_conv")
def by_conv(conversation_id: str, con: Connection = Depends(db_conn)):
    return {"rows": traces_by_conv(con, conversation_id)}
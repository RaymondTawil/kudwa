from __future__ import annotations
from fastapi import APIRouter, Query, Depends
from sqlite3 import Connection
from app.repositories.metrics import summary, trend
from app.db.db_con import db_conn

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("/summary")
def metrics_summary(
    year: int | None = Query(None),
    source: str | None = Query(None),
    con: Connection = Depends(db_conn),
):
    return summary(con, year, source)

@router.get("/trend")
def metrics_trend(
    metric: str = Query(..., pattern=r"^(revenue|cogs|gross_profit|expenses|net_profit)$"),
    year: int | None = None,
    source: str | None = None,
    con: Connection = Depends(db_conn),
):
    return trend(con, metric, year, source)
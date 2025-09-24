from __future__ import annotations
from sqlite3 import Connection
from fastapi import APIRouter, Query, Depends
from app.db.db_con import db_conn
from app.repositories.metrics import summary, trend

# Create a FastAPI router for metrics endpoints
router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("/summary")
def metrics_summary(
    year: int | None = Query(None),
    source: str | None = Query(None),
    con: Connection = Depends(db_conn),
):
    """
    API endpoint to get a summary of all metrics for a given year and/or source.
    Returns a list of metric records.
    """
    return summary(con, year, source)

@router.get("/trend")
def metrics_trend(
    metric: str = Query(..., pattern=r"^(revenue|cogs|gross_profit|expenses|net_profit)$"),
    year: int | None = None,
    source: str | None = None,
    con: Connection = Depends(db_conn),
):
    """
    API endpoint to get a time series trend for a given metric, year, and/or source.
    Returns a list of (period_end, value, source) points.
    """
    return trend(con, metric, year, source)
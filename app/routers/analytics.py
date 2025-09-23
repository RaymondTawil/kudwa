from __future__ import annotations
from fastapi import APIRouter, Query, Depends
from sqlite3 import Connection, DatabaseError
from app.services.analytics import anomalies
from app.repositories.facts import expenses_increase_top
from app.db.db_con import db_conn


router = APIRouter(prefix="/api/v1", tags=["analytics"])

@router.get("/expenses/top_increase")
def expenses_top_increase_api(
    year: int,
    source: str | None = None,
    limit: int = 5,
    con: Connection = Depends(db_conn),
):
    # Fast existence check to avoid 500s on empty years
    params = [str(year)]
    src_sql = ""
    if source:
        src_sql = " AND source=?"
        params.append(source)

    row = con.execute(
        f"SELECT COUNT(1) AS c FROM facts "
        f"WHERE category='expense' AND substr(month_key,1,4)=?{src_sql}",
        params,
    ).fetchone()
    if not row or (row["c"] or 0) == 0:
        # Always return a valid shape (HTTP 200) even if no data
        return {"year": year, "first_month": None, "last_month": None, "top": []}

    # Normal path
    return expenses_increase_top(con, year, source, limit)

@router.get("/analytics/anomalies")
def anomalies_api(
    metric: str = Query(..., pattern=r"^(revenue|cogs|gross_profit|expenses|net_profit)$"),
    year: int | None = None,
    source: str | None = None,
    z: float = 2.0,
    con: Connection = Depends(db_conn),
):
    return anomalies(con, metric, year, source, z)
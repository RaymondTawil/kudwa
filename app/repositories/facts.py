from __future__ import annotations
from sqlite3 import Connection
from app.utils.normalization import ym_key
from typing import Any, List, Dict, Optional


def insert_fact(
    con: Connection,
    period_start: str | None,
    period_end: str | None,
    source: str,
    account: str,
    category: str,
    kind: str,
    amount: float,
):
    """
    Insert a fact record into the facts table.
    Computes the month key from period_end.
    """
    mk = ym_key(period_end) if period_end else None
    with con:
        con.execute(
            """
            INSERT INTO facts(period_start, period_end, month_key, source, account, category, kind, amount)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (period_start, period_end, mk, source, account, category, kind, amount)
        )


def expenses_increase_top(
    con: Connection,
    year: int,
    source: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Returns the top accounts with the largest increase in expenses for a given year.
    Optionally filters by source and limits the number of results.
    """
    params_firstlast: List[Any] = [str(year)]
    src_clause = ""
    if source:
        src_clause = " AND source=?"
        params_firstlast.append(source)

    row = con.execute(
        f"""
        SELECT MIN(month_key) AS first, MAX(month_key) AS last
        FROM facts
        WHERE category='expense' AND substr(month_key,1,4)=?{src_clause}
        """,
        params_firstlast,
    ).fetchone()

    first = row["first"] if row else None
    last = row["last"] if row else None
    if not first or not last:
        return {"year": year, "first_month": first, "last_month": last, "top": []}

    params: List[Any] = [str(year)]
    if source:
        params.append(source)
    params.extend([first, last, limit])

    cur = con.execute(
        f"""
        WITH per_month AS (
            SELECT account, month_key, SUM(amount) AS amt
            FROM facts
            WHERE category='expense' AND substr(month_key,1,4)=?{src_clause}
            GROUP BY account, month_key
        ),
        edges AS (
            SELECT a.account,
                   (SELECT amt FROM per_month WHERE account=a.account AND month_key=?) AS first_amt,
                   (SELECT amt FROM per_month WHERE account=a.account AND month_key=?) AS last_amt
            FROM (SELECT DISTINCT account FROM per_month) a
        )
        SELECT account,
               COALESCE(last_amt,0) - COALESCE(first_amt,0) AS increase,
               COALESCE(first_amt,0) AS first,
               COALESCE(last_amt,0)  AS last
        FROM edges
        ORDER BY increase DESC
        LIMIT ?
        """,
        params,
    )
    top = [dict(r) for r in cur.fetchall()]
    return {"year": year, "first_month": first, "last_month": last, "top": top}
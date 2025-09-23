from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlite3 import Connection


def upsert_metric(con: Connection, period_end: str, source: str, revenue: float, cogs: float, expenses: float, net_profit: float | None):
    gross = (revenue or 0.0) - (cogs or 0.0)
    with con:
        con.execute(
        """
            INSERT INTO metrics(period_end, source, revenue, cogs, gross_profit, expenses, net_profit)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(period_end, source) DO UPDATE SET
            revenue=excluded.revenue,
            cogs=excluded.cogs,
            gross_profit=excluded.gross_profit,
            expenses=excluded.expenses,
            net_profit=excluded.net_profit
            """, (period_end, source, revenue, cogs, gross, expenses, net_profit)
        )


def summary(con: Connection, year: int | None, source: str | None) -> Dict[str, Any]:
    q = "SELECT period_end, source, revenue, cogs, gross_profit, expenses, net_profit FROM metrics"
    where, params = [], []
    if year: where.append("substr(period_end,1,4)=?") or params.append(str(year))
    if source:
        where.append("source=?")
        params.append(source)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY period_end"
    cur = con.execute(q, params)
    return {"rows": [dict(r) for r in cur.fetchall()]}



def trend(con: Connection, metric: str, year: int | None, source: str | None) -> Dict[str, Any]:
    q = f"SELECT period_end, {metric} as value, source FROM metrics"
    where, params = [], []
    if year: where.append("substr(period_end,1,4)=?") or params.append(str(year))
    if source:
        where.append("source=?")
        params.append(source)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY period_end"
    cur = con.execute(q, params)
    return {"metric": metric, "points": [dict(r) for r in cur.fetchall()]}



def sum_between(con, month_begin: int, month_end: int, year: int, source: str | None) -> Dict[str, float]:
    where = ["substr(period_end,1,4)=?", "CAST(substr(period_end,6,2) AS INTEGER) BETWEEN ? AND ?"]
    params: List[Any] = [str(year), month_begin, month_end]
    if source:
        where.append("source=?")
        params.append(source)
    q = f"SELECT SUM(revenue) rev, SUM(cogs) cogs, SUM(gross_profit) gp, SUM(expenses) exp, SUM(COALESCE(net_profit,0)) np FROM metrics WHERE {' AND '.join(where)}"
    r = con.execute(q, params).fetchone()
    return {"revenue": r[0] or 0.0, "cogs": r[1] or 0.0, "gross_profit": r[2] or 0.0, "expenses": r[3] or 0.0, "net_profit": r[4] or 0.0}
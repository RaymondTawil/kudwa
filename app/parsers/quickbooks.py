from __future__ import annotations
from typing import Any, Dict, List, Tuple
from sqlite3 import Connection
from app.repositories.facts import insert_fact
from app.repositories.metrics import upsert_metric
from app.utils.normalization import safe_float, ym_key


def _qb_walk_rows(rows: List[dict], header_group: str | None = None) -> List[dict]:
    flat: List[dict] = []
    for r in rows:
        if 'Rows' in r and r.get('Rows', {}).get('Row'):
            hdr = r.get('Header', {})
            account = None
            if hdr:
                coldata = hdr.get('ColData', [])
                if coldata:
                   account = coldata[0].get('value')
            flat.extend(_qb_walk_rows(r['Rows']['Row'], header_group=account))
            if 'Summary' in r:
                s = r['Summary']['ColData']
                acc = s[0]['value'] if s else (account or header_group or 'Section Total')
                vals = [c.get('value', '') for c in s[1:]]
                flat.append({'account': acc, 'values': vals, 'summary': True})
        else:
            cd = r.get('ColData', [])
            if not cd: continue
            account = cd[0].get('value', header_group or '')
            vals = [c.get('value', '') for c in cd[1:]]
            flat.append({'account': account, 'values': vals, 'summary': False})
    return flat


def _categorize(acc: str) -> str:
    a = (acc or '').lower()
    if 'income' in a or a.startswith('revenue') or 'sales' in a: return 'revenue'
    if 'cost of goods sold' in a or 'payroll expense - cos' in a or 'direct parts' in a: return 'cogs'
    if 'expense' in a or 'shipping' in a or 'technology' in a: return 'expense'
    if a.startswith('total '): return 'other'
    return 'other'


def ingest_quickbooks(con: Connection, payload: Dict[str, Any]):
    data = payload.get('data') or payload
    header = data.get('Header', {})
    cols = data.get('Columns', {}).get('Column', [])
    rows = data.get('Rows', {}).get('Row', [])


    month_cols: List[Tuple[str | None, str | None]] = []
    for c in cols[1:]:
        md = {m['Name']: m['Value'] for m in c.get('MetaData', [])} if c.get('MetaData') else {}
        start = md.get('StartDate')
        end = md.get('EndDate')
        if end is None and (c.get('ColTitle','').lower() == 'total'):
            month_cols.append((None, None))
        else:
            month_cols.append((start, end))

    flat = _qb_walk_rows(rows)


    inserted = 0
    metrics_inserted = 0
    periods_set = set()


    for item in flat:
        acc = item['account'] or 'Unknown'
        values = item['values']
        is_summary = item.get('summary', False)
        for i, (start, end) in enumerate(month_cols):
            if end is None: continue
            amt = safe_float(values[i]) if i < len(values) else 0.0
            if start and end:
                periods_set.add(end)
                insert_fact(con, start, end, 'quickbooks', acc, _categorize(acc), 'total' if is_summary else 'amount', amt)
                inserted += 1

    for pe in sorted(periods_set):
        cur = con.execute(
        """
        SELECT SUM(CASE WHEN category='revenue' THEN amount ELSE 0 END) AS revenue,
            SUM(CASE WHEN category='cogs' THEN amount ELSE 0 END) AS cogs,
            SUM(CASE WHEN category='expense' THEN amount ELSE 0 END) AS expenses
        FROM facts WHERE source='quickbooks' AND month_key=?
        """, (ym_key(pe),)
        )
        row = cur.fetchone()
        if not row: continue
        revenue = row['revenue'] or 0.0
        cogs = row['cogs'] or 0.0
        expenses = row['expenses'] or 0.0
        upsert_metric(con, period_end=pe, source='quickbooks', revenue=revenue, cogs=cogs, expenses=expenses, net_profit=None)
        metrics_inserted += 1


    return {
        'source': 'quickbooks',
        'inserted_facts': inserted,
        'inserted_metrics': metrics_inserted,
        'periods': sorted(periods_set),
    }
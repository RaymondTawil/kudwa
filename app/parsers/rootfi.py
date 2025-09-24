from __future__ import annotations
import re
from sqlite3 import Connection
from typing import Any, Dict, List, Tuple
from app.repositories.facts import insert_fact
from app.repositories.metrics import upsert_metric
from app.utils.normalization import safe_float


def _walk_line_items(node, path: List[str], acc: List[Tuple[str, float, str]]):
    """
    Recursively flattens nested line items into a list of (full_name, value, name) tuples.
    """
    name = node.get('name')
    value = safe_float(node.get('value'))
    full = " / ".join(path + [name]) if name else "Unnamed"
    acc.append((full, value, name or 'Unnamed'))
    for child in node.get('line_items', []) or []:
        _walk_line_items(child, path + [name], acc)


def ingest_rootfi(con: Connection, payload: Dict[str, Any]):
    """
    Ingests a RootFi report payload into the database.
    Flattens line items, inserts facts, and computes metrics for each period.
    """
    data = payload.get('data') if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        items = data.get('data') or data.get('items') or []
        periods = items if isinstance(items, list) else [data]
    else:
        periods = data

    inserted = 0
    metrics_inserted = 0
    periods_set = set()

    for p in periods:
        ps = p.get('period_start')
        pe = p.get('period_end')
        if not pe:
            pid = p.get('platform_id') or ""
            m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", pid)
            if m:
                ps, pe = m.group(1), m.group(2)
        if not pe:
            continue
        periods_set.add(pe)

        total_rev = 0.0
        for r in p.get('revenue', []) or []:
            flat: List[Tuple[str, float, str]] = []
            _walk_line_items(r, ["revenue"], flat)
            for full_name, val, _ in flat:
                insert_fact(con, ps, pe, 'rootfi', full_name, 'revenue', 'amount', val)
                total_rev += val
                inserted += 1

        total_cogs = 0.0
        for r in p.get('cost_of_goods_sold', []) or []:
            flat = []
            _walk_line_items(r, ["cogs"], flat)
            for full_name, val, _ in flat:
                insert_fact(con, ps, pe, 'rootfi', full_name, 'cogs', 'amount', val)
                total_cogs += val
                inserted += 1

        total_exp = 0.0
        for r in p.get('expenses', []) or []:
            flat = []
            _walk_line_items(r, ["expense"], flat)
            for full_name, val, _ in flat:
                insert_fact(con, ps, pe, 'rootfi', full_name, 'expense', 'amount', val)
                total_exp += val
                inserted += 1

        net = p.get('net_profit')
        net_f = safe_float(net) if net is not None else None
        upsert_metric(con, period_end=pe, source='rootfi', revenue=total_rev, cogs=total_cogs, expenses=total_exp, net_profit=net_f)
        metrics_inserted += 1

    return {
        'source': 'rootfi',
        'inserted_facts': inserted,
        'inserted_metrics': metrics_inserted,
        'periods': sorted(periods_set),
    }
from __future__ import annotations
from datetime import datetime
import re
from typing import Any, Tuple


MONTH_NAME_TO_NUM = {
    'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
    'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12
}
NUM_TO_MONTH = {v: k for k, v in MONTH_NAME_TO_NUM.items()}


def safe_float(x: Any) -> float:
    if x is None: return 0.0
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        s = x.strip().replace(',', '')
        if not s: return 0.0
        try: return float(s)
        except Exception: return 0.0
    return 0.0


def ym_key(dt_s: str) -> str:
    try:
        d = datetime.fromisoformat(dt_s.replace('Z',''))
        return f"{d.year:04d}-{d.month:02d}"
    except Exception:
        if re.match(r"^\d{4}-\d{2}$", dt_s):
            return dt_s
    raise


def parse_quarter(q: str) -> Tuple[int, int]:
    q = q.strip().upper()
    return {'Q1': (1,3), 'Q2': (4,6), 'Q3': (7,9), 'Q4': (10,12)}[q]
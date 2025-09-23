from __future__ import annotations
from typing import Any, Dict, List
from sqlite3 import Connection
from app.repositories.metrics import trend


def anomalies(con: Connection, metric: str, year: int | None, source: str | None, z: float = 2.0) -> Dict[str, Any]:
    tr = trend(con, metric, year, source)
    vals = [p['value'] for p in tr['points'] if p['value'] is not None]
    if len(vals) < 3:
        return {"metric": metric, "points": tr['points'], "flags": []}
    mu = sum(vals)/len(vals)
    sd = (sum((v-mu)**2 for v in vals)/(len(vals)-1)) ** 0.5 if len(vals) > 1 else 0
    flags: List[Dict[str, Any]] = []
    if sd > 0:
        for p in tr['points']:
            v = p['value']
            if v is None: continue
            zscore = (v-mu)/sd
            if abs(zscore) >= z:
                flags.append({"period_end": p['period_end'], "value": v, "z": round(zscore,2)})
    return {"metric": metric, "points": tr['points'], "flags": flags, "mu": mu, "sd": sd}
import os, math
import requests
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _get(url):
    r = requests.get(f"{BASE_URL}{url}", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_summary_consistency(ensure_ingested):
    """Direct data eval: gross_profit ≈ revenue - cogs per period."""
    out = _get("/api/v1/metrics/summary")
    rows = out["rows"]
    assert len(rows) > 0
    for r in rows:
        rev = r.get("revenue") or 0.0
        cgs = r.get("cogs") or 0.0
        gp = r.get("gross_profit") or 0.0
        assert math.isclose(gp, rev - cgs, rel_tol=1e-9, abs_tol=1e-6)


def test_trend_shape(ensure_ingested):
    t = _get("/api/v1/metrics/trend?metric=revenue")
    assert t["metric"] == "revenue"
    assert isinstance(t["points"], list) and len(t["points"]) > 0
    for p in t["points"]:
        assert "period_end" in p and "value" in p

def test_expense_increase_empty_year_returns_200():
    import requests, os
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    # Pick a year likely not in data; adjust if needed
    r = requests.get(f"{BASE_URL}/api/v1/expenses/top_increase?year=2099", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) >= {"year","first_month","last_month","top"}
    assert body["top"] == []  # empty, not error

def test_expense_increase_has_fields(ensure_ingested):
    out = _get("/api/v1/metrics/summary")
    years = sorted({int(r["period_end"][0:4]) for r in out["rows"]})
    assert len(years) >= 1
    y = years[-1]
    d = _get(f"/api/v1/expenses/top_increase?year={y}")
    # Must always have the shape and 200
    assert set(d.keys()) >= {"year", "first_month", "last_month", "top"}
    assert isinstance(d["top"], list)
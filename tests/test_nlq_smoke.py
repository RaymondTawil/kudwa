import os, re
import requests
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _post_nlq(q: str):
    r = requests.post(f"{BASE_URL}/api/v1/nlq", json={"query": q}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_nlq_revenue_trend(ensure_ingested):
    # pick an existing year
    rows = requests.get(f"{BASE_URL}/api/v1/metrics/summary", timeout=30).json()["rows"]
    year = sorted({int(r["period_end"][0:4]) for r in rows})[-1]
    out = _post_nlq(f"Show me revenue trends for {year}")
    assert "answer" in out and out["answer"]
    assert "trace" in out and isinstance(out["trace"], list)


def test_nlq_compare_quarters(ensure_ingested):
    out = _post_nlq("Compare Q1 and Q2 performance")
    assert "answer" in out and out["answer"]
    # Should contain numeric figures
    assert re.search(r"\d", out["answer"]) is not None


def test_nlq_profit_q1(ensure_ingested):
    out = _post_nlq("What was the total profit in Q1?")
    assert "answer" in out and out["answer"]
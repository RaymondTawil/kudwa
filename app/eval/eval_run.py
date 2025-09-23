"""
Eval runner for Finance AI API — LLM answers only.

- Saves CSV + JSONL under --out-dir (default: eval/)
- Tests rule-based NLQ prompts (AI answers) with per-question checks
- Tests LLM fallback prompts, forcing both model variants via X-Model header:
    * exactly 3 runs per LLM question:
        1) forced gpt-4o-mini
        2) forced gpt-4o
        3) one random (no header)
- Requires your /api/v1/nlq to accept X-Model header and to log traces via obs.

Usage:
  python app/eval/eval_run.py --base http://localhost:8000
"""

from __future__ import annotations
import argparse, csv, json, os, re, sys, time, uuid
from typing import Any, Dict, List, Tuple, Callable

import requests

# -------------------------------
# Helpers
# -------------------------------
def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def nlq(base: str, query: str, cid: str, model: str | None = None) -> Dict[str, Any]:
    headers = {"content-type": "application/json"}
    if model:
        headers["X-Model"] = model  # server must honor this to force the model
    r = requests.post(f"{base}/api/v1/nlq",
                      json={"query": query, "conversation_id": cid},
                      headers=headers, timeout=60)
    if not (200 <= r.status_code < 300):
        return {"error": r.text, "status": r.status_code}
    return r.json()

def traces_by_conv(base: str, cid: str) -> List[Dict[str, Any]]:
    try:
        r = requests.get(f"{base}/api/v1/obs/traces/by_conv",
                         params={"conversation_id": cid},
                         timeout=30)
        if r.status_code != 200:
            return []
        return r.json().get("rows", [])
    except Exception:
        return []

def latest_obs_row(base: str, cid: str) -> Dict[str, Any] | None:
    rows = traces_by_conv(base, cid)
    return rows[0] if rows else None

# -------------------------------
# Main
# -------------------------------
def main():
    # Resolve default output directory relative to this file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_out_dir = os.path.join(script_dir)  # e.g., app/eval/
    # Files default to eval/eval_report.csv and eval/answers.jsonl under this dir
    default_csv  = os.path.join(default_out_dir, "eval_report.csv")
    default_json = os.path.join(default_out_dir, "answers.jsonl")

    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.getenv("BASE_URL", "http://localhost:8000"))
    ap.add_argument("--out-dir", default=default_out_dir, help="Directory for outputs (will be created)")
    ap.add_argument("--csv",  default=None, help="CSV path; default: <out-dir>/eval_report.csv")
    ap.add_argument("--json", default=None, help="JSONL path; default: <out-dir>/answers.jsonl")
    ap.add_argument("--mini", default="gpt-4o-mini", help="Mini model variant")
    ap.add_argument("--full", default="gpt-4o", help="Full model variant")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    out_dir = args.out_dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    csv_path  = args.csv  or os.path.join(out_dir, "eval_report.csv")
    json_path = args.json or os.path.join(out_dir, "answers.jsonl")
    ensure_parent_dir(csv_path)
    ensure_parent_dir(json_path)

    # ---- Question sets (AI-only) ----
    # Rule-based (these still come from the AI layer, not direct API)
    RB_QS: List[Tuple[str, Callable[[str], bool]]] = [
        ("What was the total profit in Q1 2024?", lambda a: "profit" in a.lower()),
        ("Show me revenue trends for 2024",       lambda a: "revenue" in a.lower()),
        ("Which expense category had the highest increase 2024?", lambda a: "increase" in a.lower() or "expense" in a.lower()),
        ("Compare Q1 and Q2 performance 2024",    lambda a: ("q1" in a.lower() and "q2" in a.lower()) or "vs" in a.lower()),
    ]

    # LLM-fallback questions (should NOT match rule-based regex in your service, to exercise the LLM)
    LLM_QS: List[Tuple[str, Callable[[str], bool]]] = [
        ("Summarize our 2024 financial performance in one sentence with concrete numbers.", lambda a: len(a.strip()) > 0),
        ("In one sentence: what drove margin changes across months in 2024?",               lambda a: len(a.strip()) > 0),
        ("Identify any unusual spikes or dips in 2024 and explain them in one sentence.",   lambda a: len(a.strip()) > 0),
    ]

    # Prepare writers
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_fp, open(json_path, "w", encoding="utf-8") as json_fp:
        w = csv.writer(csv_fp)
        w.writerow([
            "ts", "kind", "question", "status",
            "latency_ms", "model", "tokens_prompt", "tokens_completion",
            "answer_len", "answer_excerpt"
        ])

        def write_jsonl(obj: Dict[str, Any]):
            json_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
            json_fp.flush()

        def run_one(kind: str, question: str, checker=None, force_model: str | None = None) -> Dict[str, Any]:
            cid = f"eval_{uuid.uuid4().hex}"
            t0 = time.perf_counter()
            resp = nlq(base, question, cid, model=force_model)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            if "error" in resp:
                row = {
                    "ts": now_iso(), "kind": kind, "question": question, "status": "http_error",
                    "latency_ms": round(dt_ms, 2), "model": force_model or None,
                    "tokens_prompt": None, "tokens_completion": None,
                    "answer": None, "answer_excerpt": resp["error"][:160], "trace": [],
                    "conversation_id": cid
                }
                w.writerow([row["ts"], kind, question, row["status"], row["latency_ms"],
                            row["model"] or "", "", "", 0, row["answer_excerpt"]])
                csv_fp.flush()
                write_jsonl(row)
                return row

            ans = resp.get("answer", "") or ""
            trace = resp.get("trace", []) or []

            # Pull model/tokens/latency from obs using conversation_id (if obs wired)
            obs = latest_obs_row(base, cid) or {}
            model = obs.get("model")  # may be None if rule-based handled it
            tokens_p = obs.get("tokens_prompt")
            tokens_c = obs.get("tokens_completion")
            latency_obs = obs.get("latency_ms")
            latency_final = latency_obs if isinstance(latency_obs, (int, float)) else dt_ms

            # Pass/fail logic
            if kind == "rb":
                passed = bool(checker(ans)) if callable(checker) else bool(ans.strip())
            else:
                passed = bool(ans.strip())

            row = {
                "ts": now_iso(), "kind": kind, "question": question,
                "status": "pass" if passed else "fail",
                "latency_ms": round(latency_final, 2),
                "model": model or (force_model or ""),  # prefer server-observed model
                "tokens_prompt": tokens_p, "tokens_completion": tokens_c,
                "answer": ans, "answer_excerpt": ans[:160].replace("\n", " "),
                "answer_len": len(ans), "trace": trace, "obs": obs, "conversation_id": cid
            }
            w.writerow([
                row["ts"], kind, question, row["status"], row["latency_ms"],
                row["model"], row["tokens_prompt"] or "", row["tokens_completion"] or "",
                row["answer_len"], row["answer_excerpt"]
            ])
            csv_fp.flush()
            write_jsonl(row)
            return row

        # 1) Rule-based NLQ (AI answers, deterministic)
        for q, check in RB_QS:
            _ = run_one("rb", q, checker=check)

        # 2) LLM fallback NLQ — exactly THREE runs per question:
        #    (1) forced mini, (2) forced full, (3) random
        for q, _check in LLM_QS:
            _ = run_one("llm", q, force_model=args.mini)  # forced gpt-4o-mini
            _ = run_one("llm", q, force_model=args.full)  # forced gpt-4o
            _ = run_one("llm", q, force_model=None)       # random/no header

    print(f"[OK] CSV saved: {csv_path}")
    print(f"[OK] JSONL saved: {json_path}")

if __name__ == "__main__":
    main()

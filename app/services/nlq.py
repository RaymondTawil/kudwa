from __future__ import annotations
import os, re, time, random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlite3 import Connection
from openai import OpenAI

from app.obs.traces import trace_log, TraceIn
from app.obs.metrics import AI_TOKENS
from app.repositories.metrics import sum_between, trend
from app.repositories.facts import expenses_increase_top
from app.utils.normalization import parse_quarter, NUM_TO_MONTH

# Documentation for available rule-based tools
TOOLBOX_DOC = {
    "get_total_profit": "Return net_profit if available else gross_profit for a time window.",
    "revenue_trend": "Return revenue by month for a year.",
    "top_expense_increase": "Return expense accounts with highest increase in the year.",
    "compare_quarters": "Compare metrics between two quarters in a year.",
}

def _ensure_conversation(con: Connection, conv_id: Optional[str]) -> str:
    """
    Ensure a conversation exists in the DB, or create a new one if not provided.
    Returns the conversation ID.
    """
    conv = conv_id or datetime.utcnow().strftime("conv_%Y%m%d%H%M%S%f")
    with con:
        con.execute("INSERT OR IGNORE INTO conversations(id, created_at) VALUES(?,?)", (conv, datetime.utcnow().isoformat()))
    return conv


def _add_message(con: Connection, conv_id: str, role: str, content: str):
    """
    Add a message to the conversation in the DB.
    """
    with con:
        con.execute("INSERT INTO messages(conv_id, role, content, ts) VALUES(?,?,?,?)", (conv_id, role, content, datetime.utcnow().isoformat()))


def _handle_rule_based(con: Connection, q: str) -> Tuple[Optional[str], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Handle simple NLQ queries using rule-based logic for speed and determinism.
    Returns (answer, data, trace) if matched, else (None, {}, trace).
    """
    trace: List[Dict[str, Any]] = []
    qn = q.lower().strip()

    # Rule: total profit in a quarter
    m = re.search(r"total (profit|net profit|gross profit) in (q[1-4])(?:\s*(\d{4}))?", qn)
    if m:
        kind, qtr, year_s = m.group(1), m.group(2).upper(), m.group(3)
        year = int(year_s or datetime.utcnow().year)
        a, b = parse_quarter(qtr)
        sums_rootfi = sum_between(con, a, b, year, source='rootfi')
        sums_qb = sum_between(con, a, b, year, source='quickbooks')
        profit = sums_rootfi['net_profit'] or sums_qb['gross_profit']
        answer = f"{qtr} {year} profit was {profit:,.2f} (net from Rootfi if available, otherwise gross)."
        data = {"rootfi": sums_rootfi, "quickbooks": sums_qb}
        trace.append({"tool": "get_total_profit", "args": {"quarter": qtr, "year": year}})
        return answer, data, trace

    # Rule: revenue trend for a year
    m = re.search(r"revenue (trend|trends).*(\d{4})", qn)
    if m:
        year = int(m.group(2))
        pts = trend(con, 'revenue', year, None)['points']
        total = sum((p['value'] or 0.0) for p in pts)
        by_month: Dict[str, float] = {}
        for p in pts:
            mnum = int(p['period_end'][5:7])
            key = NUM_TO_MONTH.get(mnum, '?')
            by_month[key] = by_month.get(key, 0.0) + (p['value'] or 0.0)
        answer = f"Revenue trend for {year}: total {total:,.2f}."
        if by_month:
            top = sorted(by_month.items(), key=lambda x: x[1], reverse=True)[:3]
            answer += " Top months: " + ", ".join(f"{k} ({v:,.0f})" for k, v in top)
        data = {"points": pts, "by_month": by_month}
        trace.append({"tool": "revenue_trend", "args": {"year": year}})
        return answer, data, trace

    # Rule: top expense increase in a year
    m = re.search(r"which (expense|expenses).*highest increase.*(\d{4})", qn)
    if m:
        year = int(m.group(2))
        detail = expenses_increase_top(con, year, None)
        top = detail.get('top') or []
        if top:
            a = top[0]
            answer = f"In {year}, '{a['account']}' had the highest increase: +{a['increase']:,.2f}."
        else:
            answer = f"No expense categories found for {year}."
        trace.append({"tool": "top_expense_increase", "args": {"year": year}})
        return answer, detail, trace

    # Rule: compare two quarters
    m = re.search(r"compare\s*(q[1-4])\s*and\s*(q[1-4])(?:\s*(\d{4}))?", qn)
    if m:
        q1, q2, year_s = m.group(1).upper(), m.group(2).upper(), m.group(3)
        year = int(year_s or datetime.utcnow().year)
        a1, b1 = parse_quarter(q1)
        a2, b2 = parse_quarter(q2)
        s1 = sum_between(con, a1, b1, year, None)
        s2 = sum_between(con, a2, b2, year, None)
        answer = (
            f"{q1} vs {q2} {year}: Revenue {s1['revenue']:,.0f} → {s2['revenue']:,.0f}, "
            f"Gross Profit {s1['gross_profit']:,.0f} → {s2['gross_profit']:,.0f}, "
            f"Expenses {s1['expenses']:,.0f} → {s2['expenses']:,.0f}."
        )
        trace.append({"tool": "compare_quarters", "args": {"q1": q1, "q2": q2, "year": year}})
        return answer, {"q1": s1, "q2": s2, "year": year}, trace

    # No rule matched
    return None, {}, trace


def nlq(
    con: Connection,
    query: str,
    conversation_id: Optional[str],
    openai_api_key: Optional[str],
    default_model_name: str,
    model_variants_str: str | None = None,
    prefer_model: str | None = None,
) -> Dict[str, Any]:
    """
    Natural-language endpoint:
      1) Try rule-based intents for determinism and speed.
      2) Fallback to OpenAI (if key present) to craft a concise narrative.
      3) Persist a reasoning trace (tool calls) + tokens + latency.
    """
    conv = _ensure_conversation(con, conversation_id)
    _add_message(con, conv, "user", query)

    start = time.perf_counter()
    answer, data, tool_trace = _handle_rule_based(con, query)

    model_used: Optional[str] = None
    prompt_tokens = completion_tokens = None

    # LLM fallback only if rule-based didn't answer AND we have an API key
    if answer is None:
        if not openai_api_key:
            # Explicitly record why we skipped the LLM
            tool_trace.append({"event": "llm_skipped", "reason": "no_openai_api_key"})
            answer = "Try: 'What was total profit in Q1 2024?' or 'Show me revenue trends for 2024'."
        else:
            try:
                client = OpenAI(api_key=openai_api_key)

                # Parse variants from config, or fall back to default
                variants = [m.strip() for m in (model_variants_str or "").split(",") if m.strip()]
                if not variants:
                    variants = [default_model_name]

                # Honor explicit forced model via header; else choose randomly
                model_used = prefer_model if prefer_model else random.choice(variants)

                sys_prompt = (
                    "You are a financial analyst over a monthly P&L SQLite DB. "
                    "Prefer one-sentence insights with concrete numbers. "
                    "If asked for profit, prefer net_profit; else gross_profit.\n"
                )
                resp = client.chat.completions.create(
                    model=model_used,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": query},
                    ],
                    temperature=0.2,
                    max_tokens=300,
                )
                msg = resp.choices[0].message
                answer = (msg.content or "").strip() or "No answer."
                
                if resp.usage:
                    prompt_tokens = getattr(resp.usage, "prompt_tokens", None)
                    completion_tokens = getattr(resp.usage, "completion_tokens", None)

                if prompt_tokens:
                    AI_TOKENS.labels("prompt", model_used).inc(prompt_tokens)
                if completion_tokens:
                    AI_TOKENS.labels("completion", model_used).inc(completion_tokens)
                
                model_used = getattr(resp, "model", None) or model_used
                tool_trace.append({"llm": "openai", "model": model_used})
            except Exception as e:
                tool_trace.append({"event": "llm_error", "error": str(e)})
                answer = f"LLM step failed: {e}. Try a simpler phrasing or use explicit endpoints."

    latency_ms = (time.perf_counter() - start) * 1000.0

    # Persist trace (model may be None if LLM not used)
    trace_log(
        con,
        TraceIn(
            ts=datetime.utcnow().isoformat(),
            conversation_id=conv,
            question=query,
            answer=answer,
            model=model_used,  # <-- None unless LLM actually ran
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            latency_ms=latency_ms,
            tool_calls=tool_trace,
        ),
    )

    _add_message(con, conv, "assistant", answer)

    return {"answer": answer, "data": data, "trace": tool_trace}
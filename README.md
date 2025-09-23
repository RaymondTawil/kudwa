# Kudwa AI — FastAPI + SQLite + NLQ (Rootfi + QuickBooks)

An API that:

* **Ingests** QuickBooks & Rootfi monthly P\&L JSON
* **Normalizes** data into SQLite (`facts`, `metrics`, …)
* **Exposes** REST endpoints (summary, trend, expense deltas, anomalies)
* **Answers natural-language questions** via rule-based intents + **LLM fallback**
* **Observability**: JSON logs, Prometheus `/metrics`, persisted traces (model, tokens, latency)

---

## 🚀 Quick Start (Docker Compose)

1. **Clone the repo**

```bash
git clone git@github.com:RaymondTawil/kudwa.git && cd kudwa
```

2. **Create `.env` at the repo root** and set at least your API key (LLM is optional; rule-based still works):

```
# LLM (optional but recommended)
OPENAI_API_KEY=sk-...

# LLM defaults (you can force a model per request with X-Model)
MODEL_NAME=gpt-4o-mini
MODEL_VARIANTS=gpt-4o-mini,gpt-4o
```

3. **Build & run**

```bash
docker compose build
docker compose up -d
```

4. **Check server logs** (service named `api`)

```bash
docker compose logs --no-color --tail=200 api
```

Service URL: **[http://localhost:8000](http://localhost:8000)**

---

## 🗄️ Database Initialization

On first start the app creates all tables automatically:

* `facts` — atomic monthly rows (source, account, category = `revenue|cogs|expense`, amount)
* `metrics` — monthly rollups (revenue, cogs, gross\_profit, expenses, net\_profit)
* `conversations`, `messages` — NLQ context history
* `ai_traces` — reasoning traces (LLM/tool calls, tokens, latency, model)

SQLite uses **WAL**; you’ll see `*.db`, `*.db-wal`, `*.db-shm` in `app/db`.

---

## 📥 Ingesting Data

Data ingestion:

```bash
# QuickBooks
( printf '{ "payload": '; cat test_data/data_set_1.json; printf ' }\n' ) \
| curl -sS -X POST http://localhost:8000/ingest/quickbooks \
    -H 'content-type: application/json' --data-binary @-

# Rootfi
( printf '{ "payload": '; cat test_data/data_set_2.json; printf ' }\n' ) \
| curl -sS -X POST http://localhost:8000/ingest/rootfi \
    -H 'content-type: application/json' --data-binary @-
```

---

## 🔌 API Overview

### Health

```bash
curl -sS http://localhost:8000/health
```

### Metrics summary (optionally filter by year/source)

```bash
curl -sS "http://localhost:8000/api/v1/metrics/summary?year=2024"
```

### Trend (metric ∈ revenue|cogs|gross\_profit|expenses|net\_profit)

```bash
curl -sS "http://localhost:8000/api/v1/metrics/trend?metric=revenue&year=2024"
```

### Highest expense increase (safe even if no data)

```bash
curl -sS "http://localhost:8000/api/v1/expenses/top_increase?year=2024"
# Returns 200 with {"top": []} if the year has no expense rows.
```

### Simple anomaly detection (z-score)

```bash
curl -sS "http://localhost:8000/api/v1/analytics/anomalies?metric=revenue&year=2024&z=2.0"
```

---

## 💬 Natural Language Query (NLQ)

Rule-based examples:

```bash
curl -sS -X POST http://localhost:8000/api/v1/nlq \
  -H 'content-type: application/json' \
  --data-raw '{"query":"What was the total profit in Q1 2024?"}'

curl -sS -X POST http://localhost:8000/api/v1/nlq \
  -H 'content-type: application/json' \
  --data-raw '{"query":"Show me revenue trends for 2024"}'

curl -sS -X POST http://localhost:8000/api/v1/nlq \
  -H 'content-type: application/json' \
  --data-raw '{"query":"Which expense category had the highest increase 2024?"}'

curl -sS -X POST http://localhost:8000/api/v1/nlq \
  -H 'content-type: application/json' \
  --data-raw '{"query":"Compare Q1 and Q2 performance 2024"}'
```

LLM fallback (requires `OPENAI_API_KEY`). You can **force** a model for testing:

```bash
# Force gpt-4o
curl -sS -X POST http://localhost:8000/api/v1/nlq \
  -H 'content-type: application/json' \
  -H 'X-Model: gpt-4o' \
  --data-raw '{"query":"Summarize our 2024 financial performance in one sentence with concrete numbers."}'
```

---

## 📊 Observability

* **Prometheus metrics:** `GET /metrics`
* **Reasoning traces:**

  * Recent → `GET /api/v1/obs/traces/recent?limit=50`
  * By conversation → `GET /api/v1/obs/traces/by_conv?conversation_id=...`
* **Logs:** structured JSON to stdout (method, path, status, latency)

---


## ✅ Tests & Evaluation

### Unit/Integration Tests (Pytest)

Location: `tests/`

Covers:

* Direct data invariants (e.g., `gross_profit ≈ revenue - cogs`)
* Endpoint shapes (summary, trend, expense increase, anomalies)
* NLQ smoke tests for the four canonical questions

Run with Docker:

```bash
# inside the running container
docker compose exec api pytest -q
```

> Tests assume the API is reachable at `http://localhost:8000` and that the two JSON datasets are ingested.

---

## 🧪 Evaluation (LLM answers only)

Run the evaluator (writes to `app/eval/` by default):

```bash
python app/eval/eval_run.py --base http://localhost:8000
# Outputs:
#   app/eval/eval_report.csv
#   app/eval/answers.jsonl
```

* Runs 4 rule-based questions and multiple LLM prompts.
* For LLM prompts: exactly **three** runs each → forced **gpt-4o-mini**, forced **gpt-4o**, then one random.
* Records latency, tokens, chosen model, and full answers.


---

**Enjoy exploring your financial data with clean APIs + AI narratives!**





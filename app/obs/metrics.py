import time
from fastapi import APIRouter, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Prometheus metric: total HTTP requests, labeled by method, path, and status
REQUESTS = Counter(
    "fa_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
# Prometheus metric: request latency in milliseconds, with custom buckets
LATENCY = Histogram(
    "fa_request_latency_ms", "Request latency (ms)", buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000)
)
# Prometheus metric: AI tokens used, labeled by kind (prompt|completion) and model
AI_TOKENS = Counter(
    "fa_ai_tokens", "AI tokens used", ["kind", "model"]
)

# FastAPI router for exposing metrics endpoint
router_metrics = APIRouter()

@router_metrics.get("/metrics")
def metrics():
    """
    Expose Prometheus metrics at /metrics endpoint.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

async def metrics_middleware(request: Request, call_next):
    """
    Middleware to record request count and latency for each HTTP request.
    """
    start = time.perf_counter()
    resp = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000.0
    REQUESTS.labels(request.method, request.url.path, str(resp.status_code)).inc()
    LATENCY.observe(dur_ms)
    return resp
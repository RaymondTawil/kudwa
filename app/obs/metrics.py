from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Request, Response
import time


REQUESTS = Counter("fa_requests_total", "Total HTTP requests", ["method","path","status"])
LATENCY = Histogram("fa_request_latency_ms", "Request latency (ms)", buckets=(5,10,25,50,100,250,500,1000,2500,5000))
AI_TOKENS = Counter("fa_ai_tokens", "AI tokens used", ["kind","model"]) # kind: prompt|completion


router_metrics = APIRouter()


@router_metrics.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    resp = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000.0
    REQUESTS.labels(request.method, request.url.path, str(resp.status_code)).inc()
    LATENCY.observe(dur_ms)
    return resp
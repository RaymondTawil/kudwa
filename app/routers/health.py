from __future__ import annotations
from fastapi import APIRouter

# Create a FastAPI router for health and root endpoints
router = APIRouter(tags=["health"])

@router.get("/")
def root():
    """
    Root endpoint providing service status and a list of available endpoints.
    """
    return {
        "ok": True,
        "service": "Finance AI API",
        "endpoints": {
            "ingest_quickbooks": "/ingest/quickbooks",
            "ingest_rootfi": "/ingest/rootfi",
            "metrics_summary": "/api/v1/metrics/summary?year=2024&source=rootfi",
            "metrics_trend": "/api/v1/metrics/trend?metric=revenue&year=2024",
            "expenses_top_increase": "/api/v1/expenses/top_increase?year=2024",
            "anomalies": "/api/v1/analytics/anomalies?metric=revenue&year=2024",
            "nlq": "/api/v1/nlq"
        }
    }

@router.get("/health")
def health():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}
from __future__ import annotations
from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlite3 import Connection

from app.config import settings
from app.db.db import get_con, init_db
from app.routers import ingest, metrics, analytics, nlq, health, obs
from app.services.ingestion import auto_ingest
from app.obs.logger import logging_middleware
from app.obs.metrics import metrics_middleware, router_metrics

# Initialize FastAPI app with metadata
app = FastAPI(title="Kudwa AI API", version="0.2.1")

# Middleware: inject a SQLite connection into each request
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """
    Middleware to attach a SQLite connection to the request state.
    """
    con: Connection = get_con(settings.db_path)
    request.state.con = con
    response = await call_next(request)
    return response

# Middleware: override FastAPI dependency for Connection to use request state
@app.middleware("http")
async def add_con_dependency(request: Request, call_next):
    """
    Middleware to override the Connection dependency for all routes.
    """
    async def _get_con():
        return request.state.con
    request.app.dependency_overrides[Connection] = _get_con
    return await call_next(request)

# Add logging and metrics middleware
app.middleware("http")(logging_middleware)
app.middleware("http")(metrics_middleware)

# Custom error handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Return a JSON response with details on validation errors.
    """
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body": exc.body})

# Startup event: initialize DB and optionally auto-ingest data
@app.on_event("startup")
def on_startup():
    """
    Initialize the database and optionally auto-ingest data on startup.
    """
    con = get_con(settings.db_path)
    init_db(con)
    app.state.con = con
    if settings.auto_ingest:
        from app.services.ingestion import auto_ingest
        auto_ingest(con, settings.qb_file, settings.rootfi_file)

# Register routers for all API endpoints
app.include_router(router_metrics)
app.include_router(obs.router)
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(metrics.router)
app.include_router(analytics.router)
app.include_router(nlq.router)
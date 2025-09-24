from __future__ import annotations
from sqlite3 import Connection
from fastapi import APIRouter, HTTPException, Depends
from app.db.db_con import db_conn
from app.domain.models import IngestBody, IngestResponse
from app.services.ingestion import ingest_quickbooks_payload, ingest_rootfi_payload

# Create a FastAPI router for ingestion endpoints
router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/quickbooks", response_model=IngestResponse)
def ingest_qb(body: IngestBody, con: Connection = Depends(db_conn)):
    """
    Ingest endpoint for QuickBooks data.
    Accepts a JSON payload and stores the data in the database.
    Returns an IngestResponse or raises HTTP 400 on error.
    """
    try:
        return ingest_quickbooks_payload(con, body.payload)
    except Exception as e:
        raise HTTPException(400, f"QuickBooks ingest failed: {e}")


@router.post("/rootfi", response_model=IngestResponse)
def ingest_rf(body: IngestBody, con: Connection = Depends(db_conn)):
    """
    Ingest endpoint for Rootfi data.
    Accepts a JSON payload and stores the data in the database.
    Returns an IngestResponse or raises HTTP 400 on error.
    """
    try:
        return ingest_rootfi_payload(con, body.payload)
    except Exception as e:
        raise HTTPException(400, f"Rootfi ingest failed: {e}")
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from sqlite3 import Connection
from app.domain.models import IngestBody, IngestResponse
from app.services.ingestion import ingest_quickbooks_payload, ingest_rootfi_payload
from app.db.db_con import db_conn


router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/quickbooks", response_model=IngestResponse)
def ingest_qb(body: IngestBody, con: Connection = Depends(db_conn)):
    try:
        return ingest_quickbooks_payload(con, body.payload)
    except Exception as e:
        raise HTTPException(400, f"QuickBooks ingest failed: {e}")


@router.post("/rootfi", response_model=IngestResponse)
def ingest_rf(body: IngestBody, con: Connection = Depends(db_conn)):
    try:
        return ingest_rootfi_payload(con, body.payload)
    except Exception as e:
        raise HTTPException(400, f"Rootfi ingest failed: {e}")
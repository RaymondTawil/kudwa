from __future__ import annotations
import json, os
from sqlite3 import Connection
from app.parsers.quickbooks import ingest_quickbooks
from app.parsers.rootfi import ingest_rootfi


def ingest_quickbooks_payload(con: Connection, payload: dict):
    """
    Ingests a QuickBooks payload using the parser and returns the result.
    """
    return ingest_quickbooks(con, payload)


def ingest_rootfi_payload(con: Connection, payload: dict):
    """
    Ingests a Rootfi payload using the parser and returns the result.
    """
    return ingest_rootfi(con, payload)


def auto_ingest(con: Connection, qb_file: str, rootfi_file: str):
    """
    Automatically ingests data from QuickBooks and Rootfi files if they exist.
    Returns a dictionary with the results for each source.
    """
    out = {}
    if os.path.exists(qb_file):
        with open(qb_file, 'r') as f:
            out['quickbooks'] = ingest_quickbooks(con, json.load(f))
    if os.path.exists(rootfi_file):
        with open(rootfi_file, 'r') as f:
            out['rootfi'] = ingest_rootfi(con, json.load(f))
    return out
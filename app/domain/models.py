from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Response model for data ingestion endpoint
class IngestResponse(BaseModel):
    source: str  # Source of the ingested data
    inserted_facts: int  # Number of facts inserted
    inserted_metrics: int  # Number of metrics inserted
    periods: List[str]  # List of periods covered by the ingestion


# Request body model for ingestion endpoint
class IngestBody(BaseModel):
    payload: Dict[str, Any]  # Raw payload data to be ingested


# Request model for natural language query (NLQ) endpoint
class NLQRequest(BaseModel):
    query: str = Field(..., description="Natural language question")  # The user's NLQ
    conversation_id: Optional[str] = None  # Optional conversation/session ID


# Response model for NLQ endpoint
class NLQResponse(BaseModel):
    answer: str  # The answer to the NLQ
    data: Dict[str, Any] = {}  # Additional data relevant to the answer
    trace: List[Dict[str, Any]] = []  # Trace of steps or reasoning for the answer
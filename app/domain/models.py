from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    source: str
    inserted_facts: int
    inserted_metrics: int
    periods: List[str]


class IngestBody(BaseModel):
    payload: Dict[str, Any]


class NLQRequest(BaseModel):
    query: str = Field(..., description="Natural language question")
    conversation_id: Optional[str] = None


class NLQResponse(BaseModel):
    answer: str
    data: Dict[str, Any] = {}
    trace: List[Dict[str, Any]] = []
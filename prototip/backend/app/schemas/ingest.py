"""
Схемы ingestion батчей событий
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


EventType = Literal["window", "afk", "web", "raw"]


class IngestEvent(BaseModel):
    seq: int = Field(..., ge=0)
    type: EventType
    ts: datetime
    data: Dict[str, Any]
    raw_bucket: Optional[str] = None
    raw_event_id: Optional[str] = None


class IngestBatchRequest(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=200)
    sent_at: Optional[datetime] = None
    events: List[IngestEvent] = Field(default_factory=list)


class IngestRejected(BaseModel):
    seq: int
    reason: str


class IngestBatchResponse(BaseModel):
    accepted: int
    rejected: List[IngestRejected] = Field(default_factory=list)


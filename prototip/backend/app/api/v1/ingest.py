"""
Ingestion API: прием батчей событий от uploader'а
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_service_db
from app.core.device_security import get_current_device
from app.models.service_db import Device, ActivityEvent
from app.schemas.ingest import IngestBatchRequest, IngestBatchResponse, IngestRejected


router = APIRouter()


@router.post("/batch", response_model=IngestBatchResponse)
async def ingest_batch(
    payload: IngestBatchRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_service_db),
):
    if payload.device_id != device.device_id:
        raise HTTPException(status_code=400, detail="device_id mismatch")

    accepted = 0
    rejected: list[IngestRejected] = []

    # Мягкая валидация + частичный accept: сохраняем всё, что можно.
    for ev in payload.events:
        if ev.seq < 0:
            rejected.append(IngestRejected(seq=ev.seq, reason="seq must be >= 0"))
            continue
        try:
            row = ActivityEvent(
                device_id=device.id,
                seq=ev.seq,
                type=ev.type,
                ts=ev.ts,
                data=ev.data or {},
                raw_bucket=ev.raw_bucket,
                raw_event_id=ev.raw_event_id,
            )
            db.add(row)
            db.flush()
            accepted += 1
        except IntegrityError:
            # дубликат (device_id, seq) — идемпотентность
            db.rollback()
            accepted += 1
        except Exception as e:
            db.rollback()
            rejected.append(IngestRejected(seq=ev.seq, reason=str(e)))

    db.commit()
    return IngestBatchResponse(accepted=accepted, rejected=rejected)


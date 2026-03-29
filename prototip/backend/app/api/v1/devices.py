"""
Enrollment и политика устройств
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_service_db
from app.core.security import get_admin_user
from app.core.device_security import get_current_device
from app.models.service_db import AppUser, Device, DeviceToken, EnrollmentCode, AppConfiguration
from app.schemas.devices import (
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DevicePolicyResponse,
    DeviceRevokeRequest,
    EnrollmentCodeCreateRequest,
    EnrollmentCodeResponse,
)


router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cfg_get(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.query(AppConfiguration).filter(AppConfiguration.key == key).first()
    if row and row.value is not None:
        return row.value
    return default


@router.post("/enroll", response_model=DeviceEnrollResponse, status_code=status.HTTP_201_CREATED)
async def enroll_device(payload: DeviceEnrollRequest, db: Session = Depends(get_service_db)):
    code_row = (
        db.query(EnrollmentCode)
        .filter(EnrollmentCode.code == payload.enrollment_code)
        .first()
    )
    if code_row is None:
        raise HTTPException(status_code=400, detail="Неверный enrollment code")

    now = _utcnow()
    if code_row.used_at is not None:
        raise HTTPException(status_code=400, detail="Enrollment code уже использован")
    if code_row.expires_at is not None and code_row.expires_at < now:
        raise HTTPException(status_code=400, detail="Enrollment code истёк")

    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if device is None:
        device = Device(
            org_id=payload.org_id or code_row.org_id,
            device_id=payload.device_id,
            hostname=payload.hostname,
            os=payload.os,
        )
        db.add(device)
        db.flush()
    else:
        if device.revoked_at is not None:
            raise HTTPException(status_code=400, detail="Устройство отозвано")
        # обновим метаданные при повторном enroll (на случай переустановки)
        device.hostname = payload.hostname or device.hostname
        device.os = payload.os or device.os
        if payload.org_id:
            device.org_id = payload.org_id

    token = secrets.token_urlsafe(32)
    token_row = DeviceToken(device_id=device.id, token=token)
    db.add(token_row)

    code_row.used_at = now
    code_row.used_by_device_id = device.id

    db.commit()
    return DeviceEnrollResponse(device_id=device.device_id, token=token)


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device_token(
    payload: DeviceRevokeRequest,
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db),
):
    token_row = db.query(DeviceToken).filter(DeviceToken.token == payload.token).first()
    if token_row is None:
        # делаем идемпотентным
        return
    if token_row.revoked_at is None:
        token_row.revoked_at = _utcnow()
        db.commit()
    return


@router.get("/policy", response_model=DevicePolicyResponse)
async def get_policy(
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_service_db),
):
    mode = (_cfg_get(db, "url_policy_mode", "full") or "full").strip()
    allow_raw = (_cfg_get(db, "url_policy_allow_domains", "") or "").strip()
    deny_raw = (_cfg_get(db, "url_policy_deny_domains", "") or "").strip()
    interval_raw = (_cfg_get(db, "uploader_sync_interval_seconds", "120") or "120").strip()

    def _split(s: str) -> list[str]:
        if not s:
            return []
        parts = []
        for p in s.replace("\n", ",").split(","):
            v = p.strip()
            if v:
                parts.append(v.lower())
        return parts

    try:
        interval = int(interval_raw)
    except ValueError:
        interval = 120

    if mode not in ("drop", "host_only", "full"):
        mode = "full"

    return DevicePolicyResponse(
        url_policy_mode=mode,  # type: ignore[arg-type]
        allow_domains=_split(allow_raw),
        deny_domains=_split(deny_raw),
        sync_interval_seconds=max(30, min(interval, 3600)),
    )


@router.post("/enrollment-codes", response_model=EnrollmentCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_enrollment_code(
    payload: EnrollmentCodeCreateRequest,
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db),
):
    existing = db.query(EnrollmentCode).filter(EnrollmentCode.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Такой code уже существует")

    row = EnrollmentCode(code=payload.code, org_id=payload.org_id, expires_at=payload.expires_at)
    db.add(row)
    db.commit()
    db.refresh(row)
    return EnrollmentCodeResponse(
        code=row.code,
        org_id=row.org_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        used_at=row.used_at,
    )


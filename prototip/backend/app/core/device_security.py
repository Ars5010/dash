"""
Авторизация устройств по device_token (отдельно от user JWT).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_service_db
from app.models.service_db import DeviceToken, Device


device_security = HTTPBearer()


def get_current_device(
    credentials: HTTPAuthorizationCredentials = Depends(device_security),
    db: Session = Depends(get_service_db),
) -> Device:
    token = (credentials.credentials or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing device token")

    token_row = (
        db.query(DeviceToken)
        .filter(DeviceToken.token == token, DeviceToken.revoked_at.is_(None))
        .first()
    )
    if token_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")

    device = (
        db.query(Device)
        .filter(Device.id == token_row.device_id, Device.revoked_at.is_(None))
        .first()
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device revoked")

    return device


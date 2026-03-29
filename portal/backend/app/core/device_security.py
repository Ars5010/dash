from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import DeviceToken, Device


device_bearer = HTTPBearer()


def get_current_device(
    cred: HTTPAuthorizationCredentials = Depends(device_bearer),
    db: Session = Depends(get_db),
) -> Device:
    token = (cred.credentials or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing device token")

    token_row = db.query(DeviceToken).filter(DeviceToken.token == token, DeviceToken.revoked_at.is_(None)).first()
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")

    device = db.query(Device).filter(Device.id == token_row.device_id, Device.revoked_at.is_(None)).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device revoked")
    return device


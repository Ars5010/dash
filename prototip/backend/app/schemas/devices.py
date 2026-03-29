"""
Схемы для enrollment/устройств
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class DeviceEnrollRequest(BaseModel):
    enrollment_code: str = Field(..., min_length=3, max_length=200)
    device_id: str = Field(..., min_length=3, max_length=200)
    org_id: Optional[str] = Field(None, max_length=100)
    hostname: Optional[str] = Field(None, max_length=200)
    os: Optional[str] = Field(None, max_length=100)


class DeviceEnrollResponse(BaseModel):
    device_id: str
    token: str
    token_type: str = "bearer"


class DevicePolicyResponse(BaseModel):
    url_policy_mode: Literal["drop", "host_only", "full"] = "full"
    allow_domains: List[str] = []
    deny_domains: List[str] = []
    sync_interval_seconds: int = 120


class DeviceRevokeRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=255)


class EnrollmentCodeCreateRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=200)
    org_id: Optional[str] = Field(None, max_length=100)
    expires_at: Optional[datetime] = None


class EnrollmentCodeResponse(BaseModel):
    code: str
    org_id: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None


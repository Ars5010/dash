"""
Схемы для пользователей
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    login: str
    password: str
    role_id: int


class UserResponse(BaseModel):
    id: int
    login: str
    role_id: int
    role_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


"""
Схемы для аутентификации
"""
from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    login: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


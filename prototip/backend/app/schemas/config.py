"""
Схемы для конфигурации
"""
from pydantic import BaseModel
from typing import Optional


class ConfigResponse(BaseModel):
    key: str
    value: Optional[str] = None


class ConfigUpdate(BaseModel):
    key: str
    value: Optional[str] = None


"""
Схемы для модуля Отпуска/Больничные
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LeaveEventCreate(BaseModel):
    user_id: int
    start_date: datetime
    end_date: datetime
    leave_type: str  # "Отпуск", "Больничный", "Праздник", "Выходной", "Прогул", "Отгул"


class LeaveEventResponse(BaseModel):
    id: int
    user_id: int
    user_login: Optional[str] = None
    start_date: datetime
    end_date: datetime
    leave_type: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


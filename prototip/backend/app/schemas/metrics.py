"""
Схемы для модуля Метрика
"""
from pydantic import BaseModel
from typing import List, Dict, Any


class MetricsRow(BaseModel):
    user: str
    data: Dict[str, Any]  # Динамические ключи типа "Q1", "Q2", "W1", "M1" и т.д.


class MetricsAggregateResponse(BaseModel):
    period_type: str  # 'week', 'month', 'quarter', 'year'
    year: int
    data: List[MetricsRow]


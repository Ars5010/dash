"""
Схемы для модуля Сводка
"""
from pydantic import BaseModel
from typing import List


class SummaryDataset(BaseModel):
    label: str
    color: str
    data: List[float]  # секунды


class SummaryHistogramResponse(BaseModel):
    labels: List[str]  # даты
    datasets: List[SummaryDataset]


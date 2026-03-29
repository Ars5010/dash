"""
Схемы для модуля Хронология
"""
from pydantic import BaseModel
from typing import List, Optional


class ManicTimeUser(BaseModel):
    user_id: int
    display_name: str


class TimelineDayMetrics(BaseModel):
    active_minutes: int
    inactive_minutes: int
    productive_minutes: int
    unproductive_minutes: int
    active_percent: float
    inactive_percent: float
    productive_percent: float
    unproductive_percent: float
    kpi_percent: float
    indicator: str  # green|yellow|red|blue
    late: bool
    early_leave: bool
    late_penalty_percent: float
    early_leave_penalty_percent: float
    day_fine: int


class TimelinePeriodStats(BaseModel):
    period: str  # month|year
    start_date: str
    end_date: str
    total_days: int
    weekend_days: int
    holiday_days: int
    working_days: int
    good_days: int
    medium_days: int
    bad_days: int
    absence_days: int


class ActivitySegment(BaseModel):
    type: str  # "Active", "Away", "Productive", "Session Locked", "Power Off"
    start: str  # ISO datetime
    end: str  # ISO datetime


class UserActivity(BaseModel):
    user_id: int
    display_name: str
    segments: List[ActivitySegment]
    metrics: Optional[TimelineDayMetrics] = None


class TimelineActivityResponse(BaseModel):
    date: str
    activities: List[UserActivity]


class TimelinePeriodStatsResponse(BaseModel):
    user_id: int
    date: str
    month: TimelinePeriodStats
    year: TimelinePeriodStats


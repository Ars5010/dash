from __future__ import annotations

from datetime import datetime
from datetime import date as date_type
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    login: str
    password: str

    @field_validator("login")
    @classmethod
    def strip_login(cls, v: str) -> str:
        return (v or "").strip()


class UserCreate(BaseModel):
    org_name: str = Field(..., description="Создаёт org при первом запуске")
    login: str
    password: str
    full_name: str | None = None
    job_title: str | None = None
    timezone: str = "Europe/Moscow"
    role: Literal["admin", "user"] = "admin"

    @field_validator("login", "org_name")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return (v or "").strip()


class UserOut(BaseModel):
    id: int
    login: str
    full_name: str | None
    job_title: str | None = None
    role: str
    timezone: str
    is_active: bool
    ai_analyze_screenshots: bool = False


# --- admin: users/devices management (portal UI)
class AdminUserCreate(BaseModel):
    login: str
    password: str
    full_name: str | None = None
    job_title: str | None = None
    timezone: str = "Europe/Moscow"
    role: Literal["admin", "user"] = "user"
    is_active: bool = True
    ai_analyze_screenshots: bool = False


class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    timezone: str | None = None
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None
    ai_analyze_screenshots: bool | None = None


class AdminResetPassword(BaseModel):
    password: str


class EnrollmentCodeCreate(BaseModel):
    code: str
    org_id: int
    user_id: int | None = None
    expires_at: datetime | None = None


class EnrollmentCodeOut(BaseModel):
    code: str
    org_id: int
    user_id: int | None
    created_at: datetime
    expires_at: datetime | None
    used_at: datetime | None


class DeviceEnrollRequest(BaseModel):
    enrollment_code: str
    device_id: str
    hostname: str | None = None
    os: str | None = None


class DeviceEnrollResponse(BaseModel):
    device_id: str
    token: str


class DeviceEnrollWithUserRequest(BaseModel):
    org_id: int
    install_secret: str
    login: str
    password: str

    @field_validator("login")
    @classmethod
    def strip_login_enroll(cls, v: str) -> str:
        return (v or "").strip()
    full_name: str | None = None
    job_title: str | None = None
    timezone: str = "Europe/Moscow"
    email: str | None = None
    device_id: str
    hostname: str | None = None
    os: str | None = None


class OrgRegistrationMeta(BaseModel):
    org_id: int
    org_name: str
    self_registration_enabled: bool


class OrgAdminSettingsOut(BaseModel):
    org_id: int
    self_registration_enabled: bool
    install_secret_configured: bool
    screenshots_enabled: bool
    ai_enabled: bool


class OrgAdminSettingsPatch(BaseModel):
    self_registration_enabled: bool | None = None
    screenshots_enabled: bool | None = None
    ai_enabled: bool | None = None


class AiScreenshotUsersPut(BaseModel):
    """Кого анализировать по скринам (остальные в организации — выкл.)."""

    user_ids: list[int] = Field(default_factory=list)


class AiOllamaHealthOut(BaseModel):
    configured: bool
    reachable: bool
    vision_model_ready: bool
    text_model_ready: bool
    models_loaded: list[str] = Field(default_factory=list)
    detail: str | None = None


class PenaltySettingsOut(BaseModel):
    """Настройки штрафов организации (GET — эффективные; PUT — полная замена в БД)."""

    enabled: bool = Field(description="Включить систему штрафов (опоздание/ранний уход + KPI + условные суммы дня)")
    late_enabled: bool = Field(description="Учитывать опоздание (в KPI)")
    early_leave_enabled: bool = Field(description="Учитывать ранний уход (в KPI)")
    mode: Literal["binary", "proportional"] = Field(description="binary: полный % за факт; proportional: по доле от рабочего окна")
    late_percent: float = Field(ge=0, le=100, description="Базовый % штрафа за опоздание")
    early_percent: float = Field(ge=0, le=100, description="Базовый % штрафа за ранний уход")
    day_fine_enabled: bool = Field(description="Начислять условные суммы за жёлтый/красный день")
    fine_yellow: int = Field(description="Условный штраф за жёлтый день (часто отрицательное)")
    fine_red: int = Field(description="Условный штраф за красный день")
    kpi_green_above: float = Field(description="KPI строго выше этого порога → зелёный день")
    kpi_yellow_above: float = Field(description="KPI строго выше этого (и не зелёный) → жёлтый")


class InstallSecretGenerated(BaseModel):
    install_secret: str = Field(..., description="Показывается один раз; передайте в установщик на ПК")


class ScreenshotUploadResponse(BaseModel):
    media_id: str
    width: int | None = None
    height: int | None = None


UrlPolicyMode = Literal["drop", "host_only", "full"]


class DevicePolicyResponse(BaseModel):
    url_policy_mode: UrlPolicyMode = "full"
    allow_domains: list[str] = []
    deny_domains: list[str] = []
    sync_interval_seconds: int = 120
    screenshots_enabled: bool = False
    screenshot_interval_seconds: int = 300
    ai_enabled: bool = False
    ai_client_allowed: bool = False


class IngestEvent(BaseModel):
    seq: int
    type: Literal["window", "afk", "web", "raw", "screenshot"]
    ts: datetime
    duration_seconds: int | None = None
    data: dict[str, Any] = {}
    raw_bucket: str | None = None
    raw_event_id: str | None = None

    @field_validator("raw_event_id", mode="before")
    @classmethod
    def raw_event_id_to_str(cls, v: Any) -> str | None:
        if v is None:
            return None
        return str(v)


class IngestBatchRequest(BaseModel):
    device_id: str
    sent_at: datetime
    events: list[IngestEvent]


class IngestRejected(BaseModel):
    seq: int
    reason: str


class IngestBatchResponse(BaseModel):
    accepted: int
    rejected: list[IngestRejected]


class AbsenceCreate(BaseModel):
    user_id: int
    start_at: datetime
    end_at: datetime
    absence_type: str


class AbsenceUpdate(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    absence_type: str | None = None


class AbsenceOut(BaseModel):
    id: int
    user_id: int
    user_login: str | None = None
    user_full_name: str | None = None
    start_at: datetime
    end_at: datetime
    absence_type: str
    created_at: datetime


class ProductivityRuleCreate(BaseModel):
    user_id: int | None = None
    rule_type: Literal["domain", "app", "title_regex"]
    pattern: str
    is_productive: bool = True
    enabled: bool = True


class ProductivityRuleOut(BaseModel):
    id: int
    user_id: int | None
    rule_type: str
    pattern: str
    is_productive: bool
    enabled: bool


class ActivitySegment(BaseModel):
    type: str
    start: datetime
    end: datetime


class DayMetrics(BaseModel):
    active_minutes: int
    inactive_minutes: int
    productive_minutes: int
    unproductive_minutes: int
    active_percent: float
    inactive_percent: float
    productive_percent: float
    unproductive_percent: float
    kpi_percent: float
    indicator: str
    late: bool
    early_leave: bool
    late_penalty_percent: float
    early_leave_penalty_percent: float
    day_fine: int


class UserActivity(BaseModel):
    user_id: int
    display_name: str
    segments: list[ActivitySegment]
    metrics: DayMetrics


class TimelineActivityResponse(BaseModel):
    date: str
    activities: list[UserActivity]


class PeriodStats(BaseModel):
    period: str
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


class PeriodStatsResponse(BaseModel):
    user_id: int
    date: str
    month: PeriodStats
    year: PeriodStats


class TimelineScreenshotItemOut(BaseModel):
    media_file_id: str
    created_at: datetime
    width: int | None = None
    height: int | None = None
    productive_score: int | None = None
    unproductive: bool | None = None
    category: str | None = None
    evidence_ru: str | None = None
    error_text: str | None = None
    analyzed_at: datetime | None = None


class UserDayScreenshotsOut(BaseModel):
    user_id: int
    screenshots: list[TimelineScreenshotItemOut]


class TimelineDayScreenshotsResponse(BaseModel):
    date: str
    users: list[UserDayScreenshotsOut]


class UserProfileDayRow(BaseModel):
    date: str
    kpi_percent: float
    indicator: str
    day_fine: int


class UserProfileResponse(BaseModel):
    user_id: int
    login: str
    full_name: str | None
    job_title: str | None = None
    timezone: str
    is_active: bool
    recent_days: list[UserProfileDayRow]
    screenshots_analyzed_30d: int
    screenshots_avg_score_30d: float | None = None
    screenshots_unproductive_30d: int = 0


class TelegramSubscriptionCreate(BaseModel):
    chat_id: str
    title: str | None = None
    enabled: bool = True


class TelegramSubscriptionOut(BaseModel):
    id: int
    chat_id: str
    title: str | None
    enabled: bool


class DeviceTokenOut(BaseModel):
    id: int
    created_at: datetime
    revoked_at: datetime | None


class DeviceOut(BaseModel):
    id: int
    device_id: str
    user_id: int | None
    user_login: str | None
    user_full_name: str | None = None
    hostname: str | None
    os: str | None
    created_at: datetime
    revoked_at: datetime | None
    last_event_at: datetime | None = None
    tokens: list[DeviceTokenOut] = []


class AdminWipeUserResponse(BaseModel):
    deleted_activity_events: int
    deleted_absence_events: int
    deleted_daily_aggregates: int
    deleted_productivity_rules: int
    unassigned_devices: int
    cleared_enrollment_links: int


class MetaStatus(BaseModel):
    bootstrapped: bool


class MeResponse(BaseModel):
    id: int
    login: str
    full_name: str | None
    role: str
    org_id: int


# --- holidays (org-wide)
HolidayKind = Literal["Праздник", "Выходной"]


class HolidayUpsert(BaseModel):
    day: date_type
    kind: HolidayKind = "Праздник"
    name: str | None = None


class HolidayOut(BaseModel):
    day: date_type
    kind: HolidayKind
    name: str | None = None


class AISummaryRequest(BaseModel):
    user_id: int
    date: str  # YYYY-MM-DD


class AISummaryResponse(BaseModel):
    summary: str
    provider: str


class ScreenshotAnalysisListOut(BaseModel):
    id: int
    media_file_id: str
    user_id: int | None
    user_login: str | None = None
    productive_score: int | None
    category: str | None
    unproductive: bool | None
    concerns: list[str] = Field(default_factory=list)
    evidence_ru: str | None
    error_text: str | None
    vision_model: str | None = None
    analyzed_at: datetime


class ScreenshotAnalyzeRequest(BaseModel):
    media_id: str


class ScreenshotAnalyzeResponse(BaseModel):
    productive_score: int
    category: str
    unproductive: bool
    concerns: list[str]
    evidence_ru: str
    vision_model: str
    raw_model_text: str | None = None


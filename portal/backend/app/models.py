from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    self_registration_enabled = Column(Boolean, nullable=False, default=False)
    install_secret_hash = Column(String(255), nullable=True)
    screenshots_enabled = Column(Boolean, nullable=False, default=False)
    ai_enabled = Column(Boolean, nullable=False, default=False)
    penalty_settings = Column(JSONB, nullable=True)

    users = relationship("User", back_populates="org", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="org", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(255), nullable=True, unique=True)
    login = Column(String(100), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="user")  # admin|user
    timezone = Column(String(64), nullable=False, default="Europe/Moscow")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ai_analyze_screenshots = Column(Boolean, nullable=False, default=False)

    org = relationship("Organization", back_populates="users")
    devices = relationship("Device", back_populates="user")
    absences = relationship("AbsenceEvent", back_populates="user", cascade="all, delete-orphan")
    productivity_rules = relationship("ProductivityRule", back_populates="user", cascade="all, delete-orphan")


class PortalConfig(Base):
    __tablename__ = "portal_config"

    key = Column(String(100), primary_key=True)
    value = Column(String(2000), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    device_id = Column(String(200), nullable=False, unique=True, index=True)
    hostname = Column(String(200), nullable=True)
    os = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    org = relationship("Organization", back_populates="devices")
    user = relationship("User", back_populates="devices")
    tokens = relationship("DeviceToken", back_populates="device", cascade="all, delete-orphan")
    events = relationship("ActivityEvent", back_populates="device", cascade="all, delete-orphan")
    media_files = relationship("MediaFile", back_populates="device")


class EnrollmentCode(Base):
    __tablename__ = "enrollment_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(200), nullable=False, unique=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", back_populates="tokens")


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        UniqueConstraint("device_id", "seq", name="uq_activity_events_device_seq"),
        Index("ix_activity_events_device_ts", "device_id", "ts"),
        Index("ix_activity_events_org_ts", "org_id", "ts"),
    )

    id = Column(BigInteger, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    seq = Column(BigInteger, nullable=False)
    type = Column(String(32), nullable=False, index=True)  # window|afk|web|raw
    ts = Column(DateTime(timezone=True), nullable=False, index=True)  # event timestamp (start)
    duration_seconds = Column(Integer, nullable=True)  # if provided by watcher
    data = Column(JSONB, nullable=False, default=dict)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    raw_bucket = Column(String(200), nullable=True)
    raw_event_id = Column(Text, nullable=True)

    device = relationship("Device", back_populates="events")


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    device = relationship("Device", back_populates="media_files")
    screenshot_analysis = relationship("ScreenshotAnalysis", back_populates="media_file", uselist=False)


class ScreenshotAnalysis(Base):
    __tablename__ = "screenshot_analyses"
    __table_args__ = (
        UniqueConstraint("media_file_id", name="uq_screenshot_analyses_media_file"),
        Index("ix_screenshot_analyses_org_analyzed", "org_id", "analyzed_at"),
        Index("ix_screenshot_analyses_user_analyzed", "user_id", "analyzed_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    media_file_id = Column(PG_UUID(as_uuid=True), ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    productive_score = Column(Integer, nullable=True)
    category = Column(String(64), nullable=True)
    unproductive = Column(Boolean, nullable=True)
    concerns = Column(JSONB, nullable=False, default=list)
    evidence_ru = Column(Text, nullable=True)
    vision_model = Column(String(120), nullable=True)
    raw_model_text = Column(Text, nullable=True)
    error_text = Column(Text, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    media_file = relationship("MediaFile", back_populates="screenshot_analysis")


class AbsenceEvent(Base):
    __tablename__ = "absence_events"
    __table_args__ = (Index("ix_absence_events_user_start", "user_id", "start_at"),)

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    absence_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="absences")


class ProductivityRule(Base):
    __tablename__ = "productivity_rules"
    __table_args__ = (Index("ix_productivity_rules_user", "user_id"),)

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null => org-level
    rule_type = Column(String(32), nullable=False)  # domain|app|title_regex
    pattern = Column(String(500), nullable=False)
    is_productive = Column(Boolean, nullable=False, default=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="productivity_rules")


class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"
    __table_args__ = (UniqueConstraint("org_id", "user_id", "day", name="uq_daily_aggregates_org_user_day"),)

    id = Column(BigInteger, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD in user's timezone

    active_seconds = Column(Integer, nullable=False, default=0)
    inactive_seconds = Column(Integer, nullable=False, default=0)
    productive_seconds = Column(Integer, nullable=False, default=0)
    unproductive_seconds = Column(Integer, nullable=False, default=0)

    active_percent = Column(Integer, nullable=False, default=0)
    inactive_percent = Column(Integer, nullable=False, default=0)
    productive_percent = Column(Integer, nullable=False, default=0)
    unproductive_percent = Column(Integer, nullable=False, default=0)
    kpi_percent_x100 = Column(Integer, nullable=False, default=0)  # store *100 to keep 2 decimals
    indicator = Column(String(16), nullable=False, default="blue")
    late = Column(Boolean, nullable=False, default=False)
    early_leave = Column(Boolean, nullable=False, default=False)
    late_penalty_x100 = Column(Integer, nullable=False, default=0)
    early_penalty_x100 = Column(Integer, nullable=False, default=0)
    day_fine = Column(Integer, nullable=False, default=0)

    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TelegramSubscription(Base):
    __tablename__ = "telegram_subscriptions"
    __table_args__ = (UniqueConstraint("org_id", "chat_id", name="uq_telegram_subscriptions_org_chat"),)

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    chat_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("org_id", "day", name="uq_holidays_org_day"),
        Index("ix_holidays_org_day", "org_id", "day"),
    )

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    day = Column(Date, nullable=False)
    kind = Column(String(50), nullable=False, default="Праздник")  # Праздник|Выходной
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


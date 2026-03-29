"""
Модели для служебной базы данных
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AppRole(Base):
    """Роли пользователей сервиса"""
    __tablename__ = "app_roles"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)

    users = relationship("AppUser", back_populates="role")


class AppUser(Base):
    """Пользователи сервиса дашбордов"""
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("app_roles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    role = relationship("AppRole", back_populates="users")
    leave_events = relationship("LeaveEvent", back_populates="user")


class LeaveEvent(Base):
    """События отсутствий"""
    __tablename__ = "leave_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    leave_type = Column(String(50), nullable=False)  # 'Отпуск', 'Больничный', 'Праздник', ...
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("AppUser", back_populates="leave_events")


class AppConfiguration(Base):
    """Конфигурация сервиса (нечувствительные данные)"""
    __tablename__ = "app_configuration"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Device(Base):
    """Устройство-агент, которое отправляет события в портал."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String(100), nullable=True, index=True)
    device_id = Column(String(200), unique=True, nullable=False, index=True)
    hostname = Column(String(200), nullable=True)
    os = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    tokens = relationship("DeviceToken", back_populates="device", cascade="all, delete-orphan")
    events = relationship("ActivityEvent", back_populates="device", cascade="all, delete-orphan")


class EnrollmentCode(Base):
    """Код первичной активации устройства (одноразовый/временный)."""
    __tablename__ = "enrollment_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(200), unique=True, nullable=False, index=True)
    org_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)


class DeviceToken(Base):
    """Токен устройства для авторизации ingestion запросов."""
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", back_populates="tokens")


class ActivityEvent(Base):
    """Принятые события ActivityWatch (нормализованный формат портала)."""
    __tablename__ = "activity_events"
    __table_args__ = (
        UniqueConstraint("device_id", "seq", name="uq_activity_events_device_seq"),
        Index("ix_activity_events_device_ts", "device_id", "ts"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    seq = Column(BigInteger, nullable=False)
    type = Column(String(32), nullable=False, index=True)  # window|afk|web|raw
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    data = Column(JSONB, nullable=False, default=dict)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    raw_bucket = Column(String(200), nullable=True)
    raw_event_id = Column(Text, nullable=True)

    device = relationship("Device", back_populates="events")


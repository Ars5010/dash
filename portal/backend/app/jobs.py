from __future__ import annotations

from datetime import datetime, timedelta, timezone, date as date_type

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.telegram import tg_send_message
from app.models import User, TelegramSubscription, MediaFile, Device, Organization, ScreenshotAnalysis
from app.ai.screenshot_analyzer import persist_screenshot_analysis


def _today_utc() -> date_type:
    return datetime.now(timezone.utc).date()


async def job_send_daily_report() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    # Import lazily to avoid circular imports with api.py
    from app.api import compute_day_from_events

    day = _today_utc() - timedelta(days=1)

    db: Session = SessionLocal()
    try:
        org_ids = [r[0] for r in db.query(User.org_id).distinct().all()]
        for org_id in org_ids:
            subs = (
                db.query(TelegramSubscription)
                .filter(TelegramSubscription.org_id == org_id, TelegramSubscription.enabled.is_(True))
                .all()
            )
            if not subs:
                continue

            users = (
                db.query(User)
                .filter(User.org_id == org_id, User.is_active.is_(True))
                .order_by(User.login.asc())
                .all()
            )
            lines = [f"<b>Отчёт за {day.isoformat()}</b>"]
            for u in users:
                _, m = compute_day_from_events(db, org_id, u.id, day)
                lines.append(f"{u.full_name or u.login}: <b>{m.kpi_percent}%</b> ({m.indicator}), штраф {m.day_fine}")
            text = "\n".join(lines)

            for s in subs:
                await tg_send_message(bot_token=settings.TELEGRAM_BOT_TOKEN, chat_id=s.chat_id, text=text)
    finally:
        db.close()


async def job_analyze_pending_screenshots() -> None:
    if not settings.OLLAMA_BASE_URL:
        return

    db: Session = SessionLocal()
    try:
        rows = (
            db.query(MediaFile)
            .outerjoin(ScreenshotAnalysis, ScreenshotAnalysis.media_file_id == MediaFile.id)
            .join(Device, Device.id == MediaFile.device_id)
            .join(User, User.id == Device.user_id)
            .join(Organization, Organization.id == MediaFile.org_id)
            .filter(
                ScreenshotAnalysis.id.is_(None),
                Organization.ai_enabled.is_(True),
                Organization.screenshots_enabled.is_(True),
                User.ai_analyze_screenshots.is_(True),
                User.is_active.is_(True),
                Device.revoked_at.is_(None),
                Device.user_id.isnot(None),
            )
            .order_by(MediaFile.created_at.asc())
            .limit(12)
            .all()
        )
        for mf in rows:
            await persist_screenshot_analysis(db, mf)
    finally:
        db.close()


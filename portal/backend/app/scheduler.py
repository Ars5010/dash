from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.jobs import job_analyze_pending_screenshots, job_send_daily_report


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    # ежедневный отчёт: 09:00 UTC (подстроим потом под локальную зону, это MVP)
    scheduler.add_job(job_send_daily_report, CronTrigger(hour=9, minute=0), id="tg_daily_report", replace_existing=True)
    scheduler.add_job(
        job_analyze_pending_screenshots,
        IntervalTrigger(minutes=2),
        id="ai_screenshot_queue",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler


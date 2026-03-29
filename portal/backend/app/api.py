from __future__ import annotations

import os
import secrets
import uuid
from collections import defaultdict
from datetime import datetime, timezone, date as date_type, timedelta
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    hash_password,
    get_current_user,
    require_admin,
)
from app.core.device_security import get_current_device
from app.core.config import settings
from app.core.gzip_request_body import GzipRequestBodyMiddleware
from app.models import (
    Organization,
    User,
    PortalConfig,
    EnrollmentCode,
    Device,
    DeviceToken,
    ActivityEvent,
    AbsenceEvent,
    ProductivityRule,
    TelegramSubscription,
    Holiday,
    DailyAggregate,
    MediaFile,
    ScreenshotAnalysis,
)
from app.schemas import (
    Token,
    LoginRequest,
    UserCreate,
    AdminUserCreate,
    AdminUserUpdate,
    AdminResetPassword,
    UserOut,
    EnrollmentCodeCreate,
    EnrollmentCodeOut,
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DevicePolicyResponse,
    IngestBatchRequest,
    IngestBatchResponse,
    IngestRejected,
    AbsenceCreate,
    AbsenceUpdate,
    AbsenceOut,
    ProductivityRuleCreate,
    ProductivityRuleOut,
    TimelineActivityResponse,
    UserActivity,
    ActivitySegment,
    DayMetrics,
    PeriodStatsResponse,
    PeriodStats,
    TelegramSubscriptionCreate,
    TelegramSubscriptionOut,
    DeviceOut,
    DeviceTokenOut,
    MetaStatus,
    MeResponse,
    HolidayUpsert,
    HolidayOut,
    AdminWipeUserResponse,
    DeviceEnrollWithUserRequest,
    OrgRegistrationMeta,
    OrgAdminSettingsOut,
    OrgAdminSettingsPatch,
    PenaltySettingsOut,
    AiScreenshotUsersPut,
    AiOllamaHealthOut,
    InstallSecretGenerated,
    ScreenshotUploadResponse,
    AISummaryRequest,
    AISummaryResponse,
    ScreenshotAnalyzeRequest,
    ScreenshotAnalyzeResponse,
    ScreenshotAnalysisListOut,
    TimelineDayScreenshotsResponse,
    UserDayScreenshotsOut,
    TimelineScreenshotItemOut,
    UserProfileResponse,
    UserProfileDayRow,
)
from app.core.telegram import tg_send_message
from app.extensions.registry import register_extensions
from app.ai.provider import get_ai_provider
from app.ai.screenshot_analyzer import persist_screenshot_analysis


def _user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        login=u.login,
        full_name=u.full_name,
        job_title=u.job_title,
        role=u.role,
        timezone=u.timezone,
        is_active=u.is_active,
        ai_analyze_screenshots=bool(u.ai_analyze_screenshots),
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ollama_api_model_names(body: Any) -> list[str]:
    """Имена из GET /api/tags (поля name/model, без digest @…)."""
    out: list[str] = []
    seen: set[str] = set()
    models = body.get("models") if isinstance(body, dict) else None
    if not isinstance(models, list):
        return out
    for m in models:
        if not isinstance(m, dict):
            continue
        for key in ("name", "model"):
            v = m.get(key)
            if not isinstance(v, str):
                continue
            s = v.strip()
            if "@" in s:
                s = s.split("@", 1)[0].strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def _ollama_norm_tag(s: str) -> str:
    return (s or "").strip().lower().replace("_", "-")


def _ollama_installed_matches(want: str, installed: list[str]) -> bool:
    """Сопоставление тега Ollama с учётом регистра, _/- и вариантов вроде gemma3n:e4b vs gemma3n:e4b-it."""
    raw = (want or "").strip()
    if "@" in raw:
        raw = raw.split("@", 1)[0].strip()
    if not raw:
        return False
    want_full = _ollama_norm_tag(raw)
    w_base, _, w_tag = want_full.partition(":")
    for inst in installed:
        i_raw = inst.strip()
        if "@" in i_raw:
            i_raw = i_raw.split("@", 1)[0].strip()
        inst_full = _ollama_norm_tag(i_raw)
        if not inst_full:
            continue
        if inst_full == want_full:
            return True
        i_base, _, i_tag = inst_full.partition(":")
        if w_base and i_base != w_base:
            continue
        if not w_tag:
            return True
        if not i_tag:
            continue
        if i_tag == w_tag:
            return True
        if i_tag.startswith(w_tag + "-") or w_tag.startswith(i_tag + "-"):
            return True
    return False


def _cfg_get(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.query(PortalConfig).filter(PortalConfig.key == key).first()
    if row and row.value is not None:
        return row.value
    return default


DEFAULT_CFG = {
    "workday_start": "09:00",
    "workday_end": "18:00",
    "break_start": "13:00",
    "break_end": "14:00",
    "late_penalty_percent": "20",
    "early_leave_penalty_percent": "10",
    "penalty_mode": "binary",  # binary|proportional
}

DEFAULT_PENALTY_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "late_enabled": True,
    "early_leave_enabled": True,
    "mode": "binary",
    "late_percent": 20.0,
    "early_percent": 10.0,
    "day_fine_enabled": True,
    "fine_yellow": -1000,
    "fine_red": -3000,
    "kpi_green_above": 50.0,
    "kpi_yellow_above": 30.0,
}


def _effective_penalty_settings(db: Session, org_id: int) -> dict[str, Any]:
    d: dict[str, Any] = {**DEFAULT_PENALTY_SETTINGS}
    mode = (_cfg_get(db, "penalty_mode", str(d["mode"])) or d["mode"]).lower()
    d["mode"] = mode if mode in ("binary", "proportional") else "binary"
    lp = _cfg_get(db, "late_penalty_percent")
    if lp is not None and str(lp).strip() != "":
        try:
            d["late_percent"] = float(lp)
        except ValueError:
            pass
    ep = _cfg_get(db, "early_leave_penalty_percent")
    if ep is not None and str(ep).strip() != "":
        try:
            d["early_percent"] = float(ep)
        except ValueError:
            pass
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org and isinstance(org.penalty_settings, dict):
        for k, v in org.penalty_settings.items():
            if k not in DEFAULT_PENALTY_SETTINGS or v is None:
                continue
            if k in ("enabled", "late_enabled", "early_leave_enabled", "day_fine_enabled"):
                d[k] = bool(v)
            elif k in ("fine_yellow", "fine_red"):
                d[k] = int(v)
            elif k in ("late_percent", "early_percent", "kpi_green_above", "kpi_yellow_above"):
                d[k] = float(v)
            elif k == "mode":
                sv = str(v).lower()
                if sv in ("binary", "proportional"):
                    d[k] = sv
    return d


def _parse_hhmm(v: str) -> tuple[int, int]:
    p = (v or "").split(":")
    if len(p) != 2:
        raise ValueError("bad time")
    return int(p[0]), int(p[1])


def _work_windows(db: Session, day: date_type):
    sh, sm = _parse_hhmm(_cfg_get(db, "workday_start", DEFAULT_CFG["workday_start"]) or DEFAULT_CFG["workday_start"])
    eh, em = _parse_hhmm(_cfg_get(db, "workday_end", DEFAULT_CFG["workday_end"]) or DEFAULT_CFG["workday_end"])
    bsh, bsm = _parse_hhmm(_cfg_get(db, "break_start", DEFAULT_CFG["break_start"]) or DEFAULT_CFG["break_start"])
    beh, bem = _parse_hhmm(_cfg_get(db, "break_end", DEFAULT_CFG["break_end"]) or DEFAULT_CFG["break_end"])
    day_start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=timezone.utc)
    day_end = datetime(day.year, day.month, day.day, eh, em, tzinfo=timezone.utc)
    br_start = datetime(day.year, day.month, day.day, bsh, bsm, tzinfo=timezone.utc)
    br_end = datetime(day.year, day.month, day.day, beh, bem, tzinfo=timezone.utc)
    return day_start, day_end, br_start, br_end


def _clip(start: datetime, end: datetime, ws: datetime, we: datetime) -> int:
    if end <= ws or start >= we:
        return 0
    s = max(start, ws)
    e = min(end, we)
    return max(0, int((e - s).total_seconds()))


def _sec_to_min(s: int) -> int:
    return int(round(s / 60))


def _indicator(kpi: float, active_sec: int, green_above: float, yellow_above: float) -> str:
    if active_sec == 0:
        return "blue"
    if kpi > green_above:
        return "green"
    if kpi > yellow_above:
        return "yellow"
    return "red"


def _rule_match(rule: ProductivityRule, ev: ActivityEvent) -> bool:
    if not rule.enabled:
        return False
    d = ev.data or {}
    if rule.rule_type == "domain":
        host = (d.get("host") or "").lower()
        pat = rule.pattern.lstrip(".").lower()
        return host == pat or host.endswith("." + pat)
    if rule.rule_type == "app":
        app_name = (d.get("app") or "").lower()
        return app_name == rule.pattern.lower()
    if rule.rule_type == "title_regex":
        title = d.get("title") or ""
        try:
            return re.search(rule.pattern, title, flags=re.IGNORECASE) is not None
        except re.error:
            return False
    return False


def _validate_password_for_bcrypt(password: str) -> None:
    # bcrypt ограничен 72 байтами (не символами). Без проверки получаем 500 при hash().
    if len((password or "").encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Пароль слишком длинный для bcrypt (ограничение 72 байта). Сделайте пароль короче.",
        )


def _build_day_metrics(
    *,
    db: Session,
    org_id: int,
    work_start: datetime,
    work_end: datetime,
    br_start: datetime,
    br_end: datetime,
    active_sec: int,
    inactive_sec: int,
    productive_sec: int,
    first_active: datetime | None,
    last_active: datetime | None,
) -> DayMetrics:
    work_seconds = max(0, int((work_end - work_start).total_seconds()))
    break_seconds = _clip(br_start, br_end, work_start, work_end)
    effective_seconds = max(1, work_seconds - break_seconds)

    productive_sec = min(productive_sec, active_sec)
    unproductive_sec = max(0, active_sec - productive_sec)

    active_pct = round(active_sec / effective_seconds * 100.0, 2)
    inactive_pct = round(inactive_sec / effective_seconds * 100.0, 2)
    productive_pct = round(productive_sec / effective_seconds * 100.0, 2)
    unproductive_pct = round(unproductive_sec / effective_seconds * 100.0, 2)

    ps = _effective_penalty_settings(db, org_id)
    master = bool(ps["enabled"])
    late_on = master and bool(ps["late_enabled"])
    early_on = master and bool(ps["early_leave_enabled"])
    mode = str(ps.get("mode", "binary")).lower()
    late_base = float(ps.get("late_percent", 20))
    early_base = float(ps.get("early_percent", 10))

    late = False
    early = False
    late_pen = 0.0
    early_pen = 0.0

    if active_sec > 0 and first_active is not None and first_active > work_start:
        late = True
        if late_on:
            if mode == "proportional":
                late_delay = int((first_active - work_start).total_seconds())
                late_pen = round(late_base * min(1.0, max(0.0, late_delay / effective_seconds)), 2)
            else:
                late_pen = round(late_base, 2)

    if active_sec > 0 and last_active is not None and last_active < work_end:
        early = True
        if early_on:
            if mode == "proportional":
                early_gap = int((work_end - last_active).total_seconds())
                early_pen = round(early_base * min(1.0, max(0.0, early_gap / effective_seconds)), 2)
            else:
                early_pen = round(early_base, 2)

    kpi = round(active_pct + 0.5 * unproductive_pct - late_pen - early_pen, 2)
    g_thr = float(ps.get("kpi_green_above", 50))
    y_thr = float(ps.get("kpi_yellow_above", 30))
    indicator = _indicator(kpi, active_sec, g_thr, y_thr)
    day_fine = 0
    if master and bool(ps.get("day_fine_enabled", True)):
        if indicator == "yellow":
            day_fine = int(ps.get("fine_yellow", -1000))
        elif indicator == "red":
            day_fine = int(ps.get("fine_red", -3000))

    return DayMetrics(
        active_minutes=_sec_to_min(active_sec),
        inactive_minutes=_sec_to_min(inactive_sec),
        productive_minutes=_sec_to_min(productive_sec),
        unproductive_minutes=_sec_to_min(unproductive_sec),
        active_percent=active_pct,
        inactive_percent=inactive_pct,
        productive_percent=productive_pct,
        unproductive_percent=unproductive_pct,
        kpi_percent=kpi,
        indicator=indicator,
        late=late,
        early_leave=early,
        late_penalty_percent=late_pen,
        early_leave_penalty_percent=early_pen,
        day_fine=day_fine,
    )


def compute_day_from_events(db: Session, org_id: int, user_id: int, day: date_type) -> tuple[list[ActivitySegment], DayMetrics]:
    day_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=timezone.utc)
    day_end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)

    events = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.org_id == org_id, ActivityEvent.user_id == user_id, ActivityEvent.ts < day_end, ActivityEvent.ts > day_start - timedelta(days=1))
        .order_by(ActivityEvent.ts.asc())
        .all()
    )

    active_segments: list[tuple[datetime, datetime]] = []
    inactive_segments: list[tuple[datetime, datetime]] = []
    for ev in events:
        if ev.type != "afk":
            continue
        dur = ev.duration_seconds or 0
        if dur <= 0:
            continue
        st = ev.ts
        en = ev.ts + timedelta(seconds=dur)
        if en <= day_start or st >= day_end:
            continue
        st = max(st, day_start)
        en = min(en, day_end)
        is_afk = bool((ev.data or {}).get("is_afk"))
        (inactive_segments if is_afk else active_segments).append((st, en))

    rules = db.query(ProductivityRule).filter(ProductivityRule.org_id == org_id, ProductivityRule.enabled.is_(True)).all()

    def _is_productive(ev: ActivityEvent) -> bool:
        matched: bool | None = None
        for r in rules:
            if r.user_id is not None and r.user_id != user_id:
                continue
            if _rule_match(r, ev):
                matched = bool(r.is_productive)
        return bool(matched) if matched is not None else False

    productive_segments: list[tuple[datetime, datetime]] = []
    for ev in events:
        if ev.type not in ("window", "web"):
            continue
        dur = ev.duration_seconds or 0
        if dur <= 0 or not _is_productive(ev):
            continue
        st = ev.ts
        en = ev.ts + timedelta(seconds=dur)
        if en <= day_start or st >= day_end:
            continue
        st = max(st, day_start)
        en = min(en, day_end)
        productive_segments.append((st, en))

    def _overlap_seconds(a: tuple[datetime, datetime], b: tuple[datetime, datetime]) -> int:
        s = max(a[0], b[0])
        e = min(a[1], b[1])
        return max(0, int((e - s).total_seconds()))

    active_sec = sum(int((en - st).total_seconds()) for st, en in active_segments)
    inactive_sec = sum(int((en - st).total_seconds()) for st, en in inactive_segments)

    productive_sec = 0
    for ps in productive_segments:
        for ac in active_segments:
            productive_sec += _overlap_seconds(ps, ac)

    work_start, work_end, br_start, br_end = _work_windows(db, day)
    first_active = min((s for s, _ in active_segments), default=None)
    last_active = max((e for _, e in active_segments), default=None)

    metrics = _build_day_metrics(
        db=db,
        org_id=org_id,
        work_start=work_start,
        work_end=work_end,
        br_start=br_start,
        br_end=br_end,
        active_sec=active_sec,
        inactive_sec=inactive_sec,
        productive_sec=productive_sec,
        first_active=first_active,
        last_active=last_active,
    )

    segs: list[ActivitySegment] = []
    for st, en in active_segments:
        segs.append(ActivitySegment(type="Active", start=st, end=en))
    for st, en in inactive_segments:
        segs.append(ActivitySegment(type="Away", start=st, end=en))
    for st, en in productive_segments:
        segs.append(ActivitySegment(type="Productive", start=st, end=en))
    segs.sort(key=lambda x: x.start)
    return segs, metrics


ALLOWED_ABSENCE_TYPES = {"Отпуск", "Больничный", "Праздник", "Выходной", "Прогул", "Отгул"}


def create_app() -> FastAPI:
    app = FastAPI(title="ActivityWatch Portal", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Uploader шлёт /api/v1/ingest/batch с Content-Encoding: gzip — без этого FastAPI падает с UnicodeDecodeError.
    app.add_middleware(GzipRequestBodyMiddleware)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    # --- meta: для UI без Swagger
    @app.get("/api/v1/meta/status", response_model=MetaStatus)
    async def meta_status(db: Session = Depends(get_db)):
        return MetaStatus(bootstrapped=db.query(User).first() is not None)

    @app.get("/api/v1/meta/me", response_model=MeResponse)
    async def meta_me(user: User = Depends(get_current_user)):
        return MeResponse(
            id=user.id,
            login=user.login,
            full_name=user.full_name,
            role=user.role,
            org_id=user.org_id,
        )

    @app.get("/api/v1/meta/org/{org_id}/registration", response_model=OrgRegistrationMeta)
    async def org_registration_meta(org_id: int, db: Session = Depends(get_db)):
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Организация не найдена")
        return OrgRegistrationMeta(
            org_id=org.id,
            org_name=org.name,
            self_registration_enabled=bool(org.self_registration_enabled),
        )

    # --- bootstrap / admin
    @app.post("/api/v1/admin/bootstrap", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    async def bootstrap_admin(payload: UserCreate, db: Session = Depends(get_db)):
        # one-time bootstrap: if any user exists -> forbid
        if db.query(User).first() is not None:
            raise HTTPException(status_code=400, detail="Already bootstrapped")

        _validate_password_for_bcrypt(payload.password)

        # Если осталась org после неудачного bootstrap (без users) — используем её.
        org = db.query(Organization).filter(Organization.name == payload.org_name).first()
        if org is None:
            org = Organization(name=payload.org_name)
            db.add(org)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                org = db.query(Organization).filter(Organization.name == payload.org_name).first()
                if org is None:
                    raise HTTPException(status_code=400, detail="Организация с таким именем уже существует")

        user = User(
            org_id=org.id,
            login=payload.login,
            email=None,
            full_name=payload.full_name,
            job_title=payload.job_title,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            timezone=payload.timezone,
            is_active=True,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Логин уже занят")
        db.refresh(user)
        return _user_out(user)

    @app.get("/api/v1/admin/users", response_model=list[UserOut])
    async def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        rows = db.query(User).filter(User.org_id == admin.org_id).order_by(User.login.asc()).all()
        return [_user_out(u) for u in rows]

    @app.get("/api/v1/admin/org/settings", response_model=OrgAdminSettingsOut)
    async def get_org_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        org = db.query(Organization).filter(Organization.id == admin.org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Организация не найдена")
        return OrgAdminSettingsOut(
            org_id=org.id,
            self_registration_enabled=bool(org.self_registration_enabled),
            install_secret_configured=bool(org.install_secret_hash),
            screenshots_enabled=bool(org.screenshots_enabled),
            ai_enabled=bool(org.ai_enabled),
        )

    @app.patch("/api/v1/admin/org/settings", response_model=OrgAdminSettingsOut)
    async def patch_org_settings(
        payload: OrgAdminSettingsPatch,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        org = db.query(Organization).filter(Organization.id == admin.org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Организация не найдена")
        if payload.self_registration_enabled is not None:
            org.self_registration_enabled = payload.self_registration_enabled
        if payload.screenshots_enabled is not None:
            org.screenshots_enabled = payload.screenshots_enabled
        if payload.ai_enabled is not None:
            org.ai_enabled = payload.ai_enabled
        db.commit()
        db.refresh(org)
        return OrgAdminSettingsOut(
            org_id=org.id,
            self_registration_enabled=bool(org.self_registration_enabled),
            install_secret_configured=bool(org.install_secret_hash),
            screenshots_enabled=bool(org.screenshots_enabled),
            ai_enabled=bool(org.ai_enabled),
        )

    @app.get("/api/v1/admin/org/penalty-settings", response_model=PenaltySettingsOut)
    async def get_penalty_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        ps = _effective_penalty_settings(db, admin.org_id)
        return PenaltySettingsOut.model_validate(ps)

    @app.put("/api/v1/admin/org/penalty-settings", response_model=PenaltySettingsOut)
    async def put_penalty_settings(
        payload: PenaltySettingsOut,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        if payload.kpi_green_above <= payload.kpi_yellow_above:
            raise HTTPException(
                status_code=400,
                detail="Порог зелёного KPI должен быть строго больше порога жёлтого",
            )
        org = db.query(Organization).filter(Organization.id == admin.org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Организация не найдена")
        org.penalty_settings = payload.model_dump()
        db.commit()
        db.refresh(org)
        return PenaltySettingsOut.model_validate(payload.model_dump())

    @app.get("/api/v1/admin/org/ollama-health", response_model=AiOllamaHealthOut)
    async def admin_ollama_health(admin: User = Depends(require_admin)):
        del admin
        base = (settings.OLLAMA_BASE_URL or "").strip()
        if not base:
            return AiOllamaHealthOut(
                configured=False,
                reachable=False,
                vision_model_ready=False,
                text_model_ready=False,
                models_loaded=[],
                detail="OLLAMA_BASE_URL не задан",
            )
        url = f"{base.rstrip('/')}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                body = r.json()
        except Exception as e:
            return AiOllamaHealthOut(
                configured=True,
                reachable=False,
                vision_model_ready=False,
                text_model_ready=False,
                models_loaded=[],
                detail=str(e)[:500],
            )
        names = _ollama_api_model_names(body)
        vm = settings.OLLAMA_VISION_MODEL.strip()
        tm = settings.OLLAMA_MODEL.strip()

        v_ok = _ollama_installed_matches(vm, names)
        t_ok = _ollama_installed_matches(tm, names)

        if v_ok and t_ok:
            detail_msg = None
        elif not names:
            detail_msg = (
                f"Ollama отвечает, но список моделей пуст. Дождитесь окончания pull в контейнере ollama "
                f"(логи: docker compose logs -f ollama) или выполните: ollama pull {tm} && ollama pull {vm}"
            )
        else:
            detail_msg = (
                f"Ожидаются «{tm}» (текст) и «{vm}» (vision). Установлено: {', '.join(names[:12])}"
                + (", …" if len(names) > 12 else "")
                + ". При необходимости: ollama pull " + tm + " && ollama pull " + vm
            )

        return AiOllamaHealthOut(
            configured=True,
            reachable=True,
            vision_model_ready=v_ok,
            text_model_ready=t_ok,
            models_loaded=names[:80],
            detail=detail_msg,
        )

    @app.put("/api/v1/admin/org/ai-screenshot-users", status_code=status.HTTP_204_NO_CONTENT)
    async def put_ai_screenshot_users(
        payload: AiScreenshotUsersPut,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        want = set(payload.user_ids)
        if want:
            found = {row[0] for row in db.query(User.id).filter(User.org_id == admin.org_id, User.id.in_(want)).all()}
            if found != want:
                raise HTTPException(status_code=400, detail="Есть пользователи не из вашей организации")
        db.query(User).filter(User.org_id == admin.org_id).update({User.ai_analyze_screenshots: False}, synchronize_session=False)
        if want:
            db.query(User).filter(User.org_id == admin.org_id, User.id.in_(want)).update(
                {User.ai_analyze_screenshots: True},
                synchronize_session=False,
            )
        db.commit()
        return None

    @app.post("/api/v1/admin/org/install-secret", response_model=InstallSecretGenerated)
    async def generate_install_secret(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        org = db.query(Organization).filter(Organization.id == admin.org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Организация не найдена")
        raw = secrets.token_urlsafe(24)
        org.install_secret_hash = hash_password(raw)
        db.commit()
        return InstallSecretGenerated(install_secret=raw)

    @app.post("/api/v1/admin/ai/summarize-day", response_model=AISummaryResponse)
    async def ai_summarize_day(
        payload: AISummaryRequest,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        org = db.query(Organization).filter(Organization.id == admin.org_id).first()
        if not org or not org.ai_enabled:
            raise HTTPException(status_code=400, detail="ИИ для организации выключен")
        u = db.query(User).filter(User.id == payload.user_id, User.org_id == admin.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        try:
            day = datetime.strptime(payload.date, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad date: {e}") from e
        day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        rows = (
            db.query(ActivityEvent)
            .filter(
                ActivityEvent.org_id == admin.org_id,
                ActivityEvent.user_id == payload.user_id,
                ActivityEvent.ts >= day_start,
                ActivityEvent.ts < day_end,
            )
            .order_by(ActivityEvent.ts.asc())
            .limit(400)
            .all()
        )
        lines: list[str] = []
        for e in rows:
            lines.append(f"{e.type} {e.ts.isoformat()} {e.data!r}")
        prompt = (
            "Кратко (на русском) опиши рабочий день сотрудника по логам активности: приложения, сайты, перерывы. "
            "Без выдуманных деталей.\n\n"
            + "\n".join(lines[:250])
        )
        provider = get_ai_provider()
        summary = await provider.summarize_text(prompt)
        return AISummaryResponse(summary=summary, provider=provider.name)

    @app.get("/api/v1/admin/ai/screenshot-analyses", response_model=list[ScreenshotAnalysisListOut])
    async def list_screenshot_analyses(
        user_id: int | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        q = (
            db.query(ScreenshotAnalysis, User.login)
            .outerjoin(User, User.id == ScreenshotAnalysis.user_id)
            .filter(ScreenshotAnalysis.org_id == admin.org_id)
            .order_by(ScreenshotAnalysis.analyzed_at.desc())
        )
        if user_id is not None:
            q = q.filter(ScreenshotAnalysis.user_id == user_id)
        rows = q.limit(limit).all()
        out: list[ScreenshotAnalysisListOut] = []
        for sa_row, login in rows:
            out.append(
                ScreenshotAnalysisListOut(
                    id=sa_row.id,
                    media_file_id=str(sa_row.media_file_id),
                    user_id=sa_row.user_id,
                    user_login=login,
                    productive_score=sa_row.productive_score,
                    category=sa_row.category,
                    unproductive=sa_row.unproductive,
                    concerns=list(sa_row.concerns or []),
                    evidence_ru=sa_row.evidence_ru,
                    error_text=sa_row.error_text,
                    vision_model=sa_row.vision_model,
                    analyzed_at=sa_row.analyzed_at,
                )
            )
        return out

    @app.post("/api/v1/admin/ai/analyze-screenshot", response_model=ScreenshotAnalyzeResponse)
    async def ai_analyze_screenshot(
        payload: ScreenshotAnalyzeRequest,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        if not settings.OLLAMA_BASE_URL:
            raise HTTPException(status_code=400, detail="OLLAMA_BASE_URL не настроен (запустите Ollama или профиль docker compose ai)")
        org = db.query(Organization).filter(Organization.id == admin.org_id).first()
        if not org or not org.ai_enabled:
            raise HTTPException(status_code=400, detail="ИИ для организации выключен")
        try:
            mid = uuid.UUID(str(payload.media_id).strip())
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Неверный media_id") from e
        mf = db.query(MediaFile).filter(MediaFile.id == mid, MediaFile.org_id == admin.org_id).first()
        if not mf:
            raise HTTPException(status_code=404, detail="Скриншот не найден")
        row = await persist_screenshot_analysis(db, mf)
        if row.error_text:
            raise HTTPException(status_code=502, detail=row.error_text)
        return ScreenshotAnalyzeResponse(
            productive_score=int(row.productive_score or 0),
            category=str(row.category or "unknown"),
            unproductive=bool(row.unproductive),
            concerns=list(row.concerns or []),
            evidence_ru=str(row.evidence_ru or ""),
            vision_model=str(row.vision_model or ""),
            raw_model_text=(row.raw_model_text or "")[:8000] if row.raw_model_text else None,
        )

    # --- admin: org-wide holidays
    @app.get("/api/v1/admin/holidays", response_model=list[HolidayOut])
    async def list_holidays(
        year: int = Query(..., ge=1970, le=2100),
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)
        rows = (
            db.query(Holiday)
            .filter(Holiday.org_id == admin.org_id, Holiday.day >= start, Holiday.day <= end)
            .order_by(Holiday.day.asc())
            .all()
        )
        return [HolidayOut(day=r.day, kind=r.kind, name=r.name) for r in rows]

    @app.put("/api/v1/admin/holidays/bulk", response_model=list[HolidayOut])
    async def upsert_holidays_bulk(
        payload: list[HolidayUpsert],
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        out: list[HolidayOut] = []
        for item in payload:
            row = db.query(Holiday).filter(Holiday.org_id == admin.org_id, Holiday.day == item.day).first()
            if row is None:
                row = Holiday(org_id=admin.org_id, day=item.day, kind=item.kind, name=item.name)
                db.add(row)
            else:
                row.kind = item.kind
                row.name = item.name
            out.append(HolidayOut(day=item.day, kind=item.kind, name=item.name))
        db.commit()
        return out

    @app.delete("/api/v1/admin/holidays/{day}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_holiday(
        day: str,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        try:
            d = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad date: {e}") from e
        row = db.query(Holiday).filter(Holiday.org_id == admin.org_id, Holiday.day == d).first()
        if not row:
            raise HTTPException(status_code=404, detail="Праздник не найден")
        db.delete(row)
        db.commit()
        return None

    @app.post("/api/v1/admin/holidays/generate-rf", response_model=list[HolidayOut])
    async def generate_rf_holidays(
        year: int = Query(..., ge=1970, le=2100),
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        # MVP: фиксированный список официальных дат без переносов выходных.
        fixed = [
            (1, 1, "Новый год"),
            (1, 2, "Новогодние каникулы"),
            (1, 3, "Новогодние каникулы"),
            (1, 4, "Новогодние каникулы"),
            (1, 5, "Новогодние каникулы"),
            (1, 6, "Рождество"),
            (1, 7, "Новогодние каникулы"),
            (1, 8, "Новогодние каникулы"),
            (2, 23, "День защитника Отечества"),
            (3, 8, "Международный женский день"),
            (5, 1, "Праздник Весны и Труда"),
            (5, 9, "День Победы"),
            (6, 12, "День России"),
            (11, 4, "День народного единства"),
        ]
        out: list[HolidayOut] = []
        for m, d, name in fixed:
            day = date_type(year, m, d)
            row = db.query(Holiday).filter(Holiday.org_id == admin.org_id, Holiday.day == day).first()
            if row is None:
                row = Holiday(org_id=admin.org_id, day=day, kind="Праздник", name=name)
                db.add(row)
            else:
                row.kind = "Праздник"
                row.name = name
            out.append(HolidayOut(day=day, kind="Праздник", name=name))
        db.commit()
        return out

    @app.post("/api/v1/admin/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    async def create_user(payload: AdminUserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        _validate_password_for_bcrypt(payload.password)
        existing = db.query(User).filter(User.login == payload.login).first()
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
        row = User(
            org_id=admin.org_id,
            login=payload.login,
            email=None,
            full_name=payload.full_name,
            job_title=payload.job_title,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            timezone=payload.timezone,
            is_active=payload.is_active,
            ai_analyze_screenshots=payload.ai_analyze_screenshots,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _user_out(row)

    @app.patch("/api/v1/admin/users/{user_id}", response_model=UserOut)
    async def update_user(
        user_id: int,
        payload: AdminUserUpdate,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        u = db.query(User).filter(User.id == user_id, User.org_id == admin.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        if payload.full_name is not None:
            u.full_name = payload.full_name
        if payload.job_title is not None:
            u.job_title = payload.job_title
        if payload.timezone is not None:
            u.timezone = payload.timezone
        if payload.role is not None:
            u.role = payload.role
        if payload.is_active is not None:
            u.is_active = payload.is_active
        if payload.ai_analyze_screenshots is not None:
            u.ai_analyze_screenshots = payload.ai_analyze_screenshots
        db.commit()
        db.refresh(u)
        return _user_out(u)

    @app.post("/api/v1/admin/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
    async def reset_password(
        user_id: int,
        payload: AdminResetPassword,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        _validate_password_for_bcrypt(payload.password)
        u = db.query(User).filter(User.id == user_id, User.org_id == admin.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        u.hashed_password = hash_password(payload.password)
        db.commit()
        return None

    @app.post("/api/v1/admin/users/{user_id}/wipe-data", response_model=AdminWipeUserResponse)
    async def wipe_user_data(
        user_id: int,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        if user_id == admin.id:
            raise HTTPException(status_code=400, detail="Нельзя сбросить данные текущего администратора")
        u = db.query(User).filter(User.id == user_id, User.org_id == admin.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        deleted_activity = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.org_id == admin.org_id, ActivityEvent.user_id == user_id)
            .delete(synchronize_session=False)
        )
        deleted_absence = (
            db.query(AbsenceEvent)
            .filter(AbsenceEvent.org_id == admin.org_id, AbsenceEvent.user_id == user_id)
            .delete(synchronize_session=False)
        )
        deleted_aggregates = (
            db.query(DailyAggregate)
            .filter(DailyAggregate.org_id == admin.org_id, DailyAggregate.user_id == user_id)
            .delete(synchronize_session=False)
        )
        deleted_rules = (
            db.query(ProductivityRule)
            .filter(ProductivityRule.org_id == admin.org_id, ProductivityRule.user_id == user_id)
            .delete(synchronize_session=False)
        )
        unassigned_devices = (
            db.query(Device)
            .filter(Device.org_id == admin.org_id, Device.user_id == user_id)
            .update({Device.user_id: None}, synchronize_session=False)
        )
        cleared_enrollment = (
            db.query(EnrollmentCode)
            .filter(EnrollmentCode.org_id == admin.org_id, EnrollmentCode.user_id == user_id)
            .update({EnrollmentCode.user_id: None}, synchronize_session=False)
        )

        db.commit()
        return AdminWipeUserResponse(
            deleted_activity_events=int(deleted_activity or 0),
            deleted_absence_events=int(deleted_absence or 0),
            deleted_daily_aggregates=int(deleted_aggregates or 0),
            deleted_productivity_rules=int(deleted_rules or 0),
            unassigned_devices=int(unassigned_devices or 0),
            cleared_enrollment_links=int(cleared_enrollment or 0),
        )

    @app.delete("/api/v1/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_user(
        user_id: int,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        if user_id == admin.id:
            raise HTTPException(status_code=400, detail="Нельзя удалить текущего администратора")
        u = db.query(User).filter(User.id == user_id, User.org_id == admin.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Защита от случайного удаления с данными/связями. Сначала wipe-data.
        has_events = db.query(ActivityEvent.id).filter(ActivityEvent.org_id == admin.org_id, ActivityEvent.user_id == user_id).first() is not None
        has_abs = db.query(AbsenceEvent.id).filter(AbsenceEvent.org_id == admin.org_id, AbsenceEvent.user_id == user_id).first() is not None
        has_aggr = db.query(DailyAggregate.id).filter(DailyAggregate.org_id == admin.org_id, DailyAggregate.user_id == user_id).first() is not None
        has_rules = db.query(ProductivityRule.id).filter(ProductivityRule.org_id == admin.org_id, ProductivityRule.user_id == user_id).first() is not None
        has_device_links = db.query(Device.id).filter(Device.org_id == admin.org_id, Device.user_id == user_id).first() is not None
        has_enroll_links = db.query(EnrollmentCode.id).filter(EnrollmentCode.org_id == admin.org_id, EnrollmentCode.user_id == user_id).first() is not None
        if any([has_events, has_abs, has_aggr, has_rules, has_device_links, has_enroll_links]):
            raise HTTPException(status_code=400, detail="Нельзя удалить пользователя: есть связанные данные. Сначала нажмите «Сбросить данные» (wipe).")

        db.delete(u)
        db.commit()
        return None

    @app.get("/api/v1/admin/devices", response_model=list[DeviceOut])
    async def list_devices(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        # MVP: last_event_at computed via scalar subquery per device (OK for small orgs)
        devices = db.query(Device).filter(Device.org_id == admin.org_id).order_by(Device.created_at.desc()).all()
        out: list[DeviceOut] = []
        for d in devices:
            last = (
                db.query(ActivityEvent.ts)
                .filter(ActivityEvent.device_id == d.id)
                .order_by(ActivityEvent.ts.desc())
                .limit(1)
                .scalar()
            )
            out.append(
                DeviceOut(
                    id=d.id,
                    device_id=d.device_id,
                    user_id=d.user_id,
                    user_login=d.user.login if d.user else None,
                    user_full_name=d.user.full_name if d.user else None,
                    hostname=d.hostname,
                    os=d.os,
                    created_at=d.created_at,
                    revoked_at=d.revoked_at,
                    last_event_at=last,
                    tokens=[
                        DeviceTokenOut(id=t.id, created_at=t.created_at, revoked_at=t.revoked_at)
                        for t in sorted(d.tokens or [], key=lambda x: x.created_at, reverse=True)
                    ],
                )
            )
        return out

    @app.post("/api/v1/admin/devices/{device_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
    async def revoke_device(device_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        d = db.query(Device).filter(Device.id == device_id, Device.org_id == admin.org_id).first()
        if not d:
            raise HTTPException(status_code=404, detail="Устройство не найдено")
        now = _utcnow()
        d.revoked_at = now
        for t in d.tokens or []:
            if t.revoked_at is None:
                t.revoked_at = now
        db.commit()
        return None

    # --- auth
    @app.post("/api/v1/auth/token", response_model=Token)
    async def login(payload: LoginRequest, db: Session = Depends(get_db)):
        if not payload.login:
            raise HTTPException(status_code=400, detail="Введите логин")
        if db.query(User).first() is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Портал ещё не настроен. Откройте страницу /setup и создайте организацию и администратора.",
            )
        user = db.query(User).filter(User.login == payload.login, User.is_active.is_(True)).first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
        access_token = create_access_token(subject=str(user.id), role=user.role)
        return Token(access_token=access_token)

    # --- telegram subscriptions + manual report trigger
    @app.get("/api/v1/telegram/subscriptions", response_model=list[TelegramSubscriptionOut])
    async def list_tg_subs(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        rows = db.query(TelegramSubscription).filter(TelegramSubscription.org_id == admin.org_id).order_by(TelegramSubscription.id.asc()).all()
        return [TelegramSubscriptionOut(id=r.id, chat_id=r.chat_id, title=r.title, enabled=r.enabled) for r in rows]

    @app.post("/api/v1/telegram/subscriptions", response_model=TelegramSubscriptionOut, status_code=status.HTTP_201_CREATED)
    async def add_tg_sub(payload: TelegramSubscriptionCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        row = TelegramSubscription(org_id=admin.org_id, chat_id=payload.chat_id, title=payload.title, enabled=payload.enabled)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="chat_id already subscribed")
        db.refresh(row)
        return TelegramSubscriptionOut(id=row.id, chat_id=row.chat_id, title=row.title, enabled=row.enabled)

    @app.post("/api/v1/telegram/send-daily-report", status_code=status.HTTP_202_ACCEPTED)
    async def send_daily_report(
        date: str = Query(..., description="YYYY-MM-DD (UTC in MVP)"),
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not configured")
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad date: {e}") from e

        users = db.query(User).filter(User.org_id == admin.org_id, User.is_active.is_(True)).order_by(User.login.asc()).all()
        lines = [f"<b>Отчёт за {day.isoformat()}</b>"]
        for u in users:
            _, m = compute_day_from_events(db, admin.org_id, u.id, day)
            fine = m.day_fine
            lines.append(f"{u.full_name or u.login}: <b>{m.kpi_percent}%</b> ({m.indicator}), штраф {fine}")
        text = "\n".join(lines)

        subs = db.query(TelegramSubscription).filter(TelegramSubscription.org_id == admin.org_id, TelegramSubscription.enabled.is_(True)).all()
        if not subs:
            raise HTTPException(status_code=400, detail="No enabled telegram subscriptions")
        for s in subs:
            await tg_send_message(bot_token=settings.TELEGRAM_BOT_TOKEN, chat_id=s.chat_id, text=text)
        return {"sent": len(subs)}

    # --- devices
    @app.post("/api/v1/devices/enroll-with-user", response_model=DeviceEnrollResponse, status_code=status.HTTP_201_CREATED)
    async def enroll_with_user(payload: DeviceEnrollWithUserRequest, db: Session = Depends(get_db)):
        org = db.query(Organization).filter(Organization.id == payload.org_id).first()
        if not org:
            raise HTTPException(status_code=400, detail="Организация не найдена")
        if not org.self_registration_enabled:
            raise HTTPException(status_code=403, detail="Саморегистрация отключена")
        if not org.install_secret_hash or not verify_password(payload.install_secret, org.install_secret_hash):
            raise HTTPException(status_code=400, detail="Неверный ключ установки")
        _validate_password_for_bcrypt(payload.password)
        existing = db.query(User).filter(User.login == payload.login).first()
        if existing:
            raise HTTPException(status_code=400, detail="Логин уже занят")
        if payload.email:
            ex_email = db.query(User).filter(User.email == payload.email).first()
            if ex_email:
                raise HTTPException(status_code=400, detail="Email уже занят")
        user = User(
            org_id=org.id,
            login=payload.login,
            email=(payload.email.strip() if payload.email else None),
            full_name=payload.full_name,
            job_title=payload.job_title,
            hashed_password=hash_password(payload.password),
            role="user",
            timezone=payload.timezone or "Europe/Moscow",
            is_active=True,
        )
        db.add(user)
        db.flush()

        device = db.query(Device).filter(Device.device_id == payload.device_id).first()
        if device is None:
            device = Device(
                org_id=org.id,
                user_id=user.id,
                device_id=payload.device_id,
                hostname=payload.hostname,
                os=payload.os,
            )
            db.add(device)
            db.flush()
        else:
            if device.revoked_at is not None:
                raise HTTPException(status_code=400, detail="Устройство отозвано")
            device.hostname = payload.hostname or device.hostname
            device.os = payload.os or device.os
            device.org_id = org.id
            device.user_id = user.id

        token = secrets.token_urlsafe(32)
        token_row = DeviceToken(device_id=device.id, token=token)
        db.add(token_row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Не удалось зарегистрировать устройство или пользователя")
        return DeviceEnrollResponse(device_id=device.device_id, token=token)

    @app.post("/api/v1/devices/enrollment-codes", response_model=EnrollmentCodeOut, status_code=status.HTTP_201_CREATED)
    async def create_enrollment_code(payload: EnrollmentCodeCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        if payload.org_id != admin.org_id:
            raise HTTPException(status_code=400, detail="org mismatch")
        existing = db.query(EnrollmentCode).filter(EnrollmentCode.code == payload.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="code already exists")
        row = EnrollmentCode(code=payload.code, org_id=payload.org_id, user_id=payload.user_id, expires_at=payload.expires_at)
        db.add(row)
        db.commit()
        db.refresh(row)
        return EnrollmentCodeOut(
            code=row.code,
            org_id=row.org_id,
            user_id=row.user_id,
            created_at=row.created_at,
            expires_at=row.expires_at,
            used_at=row.used_at,
        )

    @app.post("/api/v1/devices/enroll", response_model=DeviceEnrollResponse, status_code=status.HTTP_201_CREATED)
    async def enroll(payload: DeviceEnrollRequest, db: Session = Depends(get_db)):
        code_row = db.query(EnrollmentCode).filter(EnrollmentCode.code == payload.enrollment_code).first()
        if not code_row:
            raise HTTPException(status_code=400, detail="Неверный enrollment code")
        now = _utcnow()
        if code_row.used_at is not None:
            raise HTTPException(status_code=400, detail="Enrollment code уже использован")
        if code_row.expires_at is not None and code_row.expires_at < now:
            raise HTTPException(status_code=400, detail="Enrollment code истёк")

        device = db.query(Device).filter(Device.device_id == payload.device_id).first()
        if device is None:
            device = Device(
                org_id=code_row.org_id,
                user_id=code_row.user_id,
                device_id=payload.device_id,
                hostname=payload.hostname,
                os=payload.os,
            )
            db.add(device)
            db.flush()
        else:
            if device.revoked_at is not None:
                raise HTTPException(status_code=400, detail="Устройство отозвано")
            device.hostname = payload.hostname or device.hostname
            device.os = payload.os or device.os
            device.org_id = code_row.org_id
            device.user_id = code_row.user_id

        token = secrets.token_urlsafe(32)
        token_row = DeviceToken(device_id=device.id, token=token)
        db.add(token_row)

        code_row.used_at = now
        code_row.used_by_device_id = device.id

        db.commit()
        return DeviceEnrollResponse(device_id=device.device_id, token=token)

    def _cfg_get(db: Session, key: str, default: str | None = None) -> str | None:
        row = db.query(PortalConfig).filter(PortalConfig.key == key).first()
        if row and row.value is not None:
            return row.value
        return default

    @app.get("/api/v1/devices/policy", response_model=DevicePolicyResponse)
    async def policy(device: Device = Depends(get_current_device), db: Session = Depends(get_db)):
        mode = (_cfg_get(db, "url_policy_mode", "full") or "full").strip()
        allow_raw = (_cfg_get(db, "url_policy_allow_domains", "") or "").strip()
        deny_raw = (_cfg_get(db, "url_policy_deny_domains", "") or "").strip()
        interval_raw = (_cfg_get(db, "uploader_sync_interval_seconds", "120") or "120").strip()

        def _split(s: str) -> list[str]:
            if not s:
                return []
            parts: list[str] = []
            for p in s.replace("\n", ",").split(","):
                v = p.strip()
                if v:
                    parts.append(v.lower())
            return parts

        try:
            interval = int(interval_raw)
        except ValueError:
            interval = 120

        if mode not in ("drop", "host_only", "full"):
            mode = "full"

        org_row = db.query(Organization).filter(Organization.id == device.org_id).first()
        screenshots_enabled = bool(org_row and org_row.screenshots_enabled)
        ai_enabled = bool(org_row and org_row.ai_enabled)
        shot_iv_raw = (_cfg_get(db, "screenshot_interval_seconds", "300") or "300").strip()
        try:
            shot_iv = int(shot_iv_raw)
        except ValueError:
            shot_iv = 300

        return DevicePolicyResponse(
            url_policy_mode=mode,  # type: ignore[arg-type]
            allow_domains=_split(allow_raw),
            deny_domains=_split(deny_raw),
            sync_interval_seconds=max(30, min(interval, 3600)),
            screenshots_enabled=screenshots_enabled,
            screenshot_interval_seconds=max(60, min(shot_iv, 3600)),
            ai_enabled=ai_enabled,
            ai_client_allowed=ai_enabled,
        )

    @app.post("/api/v1/devices/screenshots", response_model=ScreenshotUploadResponse)
    async def upload_screenshot(
        device: Device = Depends(get_current_device),
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
    ):
        org = db.query(Organization).filter(Organization.id == device.org_id).first()
        if not org or not org.screenshots_enabled:
            raise HTTPException(status_code=403, detail="Скриншоты отключены для организации")
        body = await file.read()
        if not body or len(body) > 8 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Файл пустой или слишком большой (макс. 8 МБ)")
        media_id = uuid.uuid4()
        content_type = (file.content_type or "application/octet-stream").split(";")[0].strip()
        root = Path(settings.MEDIA_ROOT)
        sub = root / str(device.org_id) / str(device.id)
        sub.mkdir(parents=True, exist_ok=True)
        ext = ".png" if "png" in content_type else ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".bin"
        rel = f"{device.org_id}/{device.id}/{media_id}{ext}"
        dest = root / rel
        dest.write_bytes(body)
        mf = MediaFile(
            id=media_id,
            org_id=device.org_id,
            device_id=device.id,
            content_type=content_type,
            storage_path=rel,
        )
        db.add(mf)
        db.commit()
        return ScreenshotUploadResponse(media_id=str(media_id))

    # --- ingest
    @app.post("/api/v1/ingest/batch", response_model=IngestBatchResponse)
    async def ingest_batch(
        payload: IngestBatchRequest,
        device: Device = Depends(get_current_device),
        db: Session = Depends(get_db),
    ):
        if payload.device_id != device.device_id:
            raise HTTPException(status_code=400, detail="device_id mismatch")

        accepted = 0
        rejected: list[IngestRejected] = []

        for ev in payload.events:
            if ev.seq < 0:
                rejected.append(IngestRejected(seq=ev.seq, reason="seq must be >= 0"))
                continue
            if ev.type == "screenshot":
                mid_raw = (ev.data or {}).get("media_id")
                if not mid_raw:
                    rejected.append(IngestRejected(seq=ev.seq, reason="screenshot requires media_id"))
                    continue
                try:
                    mid = uuid.UUID(str(mid_raw))
                except ValueError:
                    rejected.append(IngestRejected(seq=ev.seq, reason="invalid media_id"))
                    continue
                mf = (
                    db.query(MediaFile)
                    .filter(MediaFile.id == mid, MediaFile.device_id == device.id, MediaFile.org_id == device.org_id)
                    .first()
                )
                if not mf:
                    rejected.append(IngestRejected(seq=ev.seq, reason="media not found for device"))
                    continue
            try:
                row = ActivityEvent(
                    org_id=device.org_id,
                    device_id=device.id,
                    user_id=device.user_id,
                    seq=ev.seq,
                    type=ev.type,
                    ts=ev.ts,
                    duration_seconds=ev.duration_seconds,
                    data=ev.data or {},
                    raw_bucket=ev.raw_bucket,
                    raw_event_id=ev.raw_event_id,
                )
                db.add(row)
                db.flush()
                accepted += 1
            except IntegrityError:
                db.rollback()
                accepted += 1
            except Exception as e:
                db.rollback()
                rejected.append(IngestRejected(seq=ev.seq, reason=str(e)))

        db.commit()
        return IngestBatchResponse(accepted=accepted, rejected=rejected)

    # --- absence
    @app.get("/api/v1/absence/events", response_model=list[AbsenceOut])
    async def list_absence(
        start_at: datetime = Query(...),
        end_at: datetime = Query(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        if start_at > end_at:
            raise HTTPException(status_code=400, detail="start_at must be <= end_at")
        rows = (
            db.query(AbsenceEvent)
            .join(User, User.id == AbsenceEvent.user_id)
            .filter(AbsenceEvent.org_id == user.org_id, AbsenceEvent.start_at <= end_at, AbsenceEvent.end_at >= start_at)
            .all()
        )
        out: list[AbsenceOut] = []
        for r in rows:
            out.append(
                AbsenceOut(
                    id=r.id,
                    user_id=r.user_id,
                    user_login=r.user.login if r.user else None,
                    user_full_name=r.user.full_name if r.user else None,
                    start_at=r.start_at,
                    end_at=r.end_at,
                    absence_type=r.absence_type,
                    created_at=r.created_at,
                )
            )
        return out

    @app.post("/api/v1/absence/events", response_model=AbsenceOut, status_code=status.HTTP_201_CREATED)
    async def create_absence(payload: AbsenceCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        if payload.start_at > payload.end_at:
            raise HTTPException(status_code=400, detail="start_at must be <= end_at")
        if payload.absence_type not in ALLOWED_ABSENCE_TYPES:
            raise HTTPException(status_code=400, detail="Недопустимый тип отсутствия")
        u = db.query(User).filter(User.id == payload.user_id, User.org_id == admin.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        overlapping = (
            db.query(AbsenceEvent)
            .filter(
                AbsenceEvent.org_id == admin.org_id,
                AbsenceEvent.user_id == payload.user_id,
                AbsenceEvent.start_at <= payload.end_at,
                AbsenceEvent.end_at >= payload.start_at,
            )
            .first()
        )
        if overlapping:
            raise HTTPException(status_code=400, detail="Уже есть событие в этом периоде для пользователя")
        row = AbsenceEvent(org_id=admin.org_id, user_id=payload.user_id, start_at=payload.start_at, end_at=payload.end_at, absence_type=payload.absence_type)
        db.add(row)
        db.commit()
        db.refresh(row)
        return AbsenceOut(
            id=row.id,
            user_id=row.user_id,
            user_login=u.login,
            user_full_name=u.full_name,
            start_at=row.start_at,
            end_at=row.end_at,
            absence_type=row.absence_type,
            created_at=row.created_at,
        )

    @app.patch("/api/v1/absence/events/{event_id}", response_model=AbsenceOut)
    async def update_absence(
        event_id: int,
        payload: AbsenceUpdate,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        row = db.query(AbsenceEvent).filter(AbsenceEvent.id == event_id, AbsenceEvent.org_id == admin.org_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Событие не найдено")

        new_start = payload.start_at or row.start_at
        new_end = payload.end_at or row.end_at
        new_type = payload.absence_type or row.absence_type

        if new_start > new_end:
            raise HTTPException(status_code=400, detail="start_at must be <= end_at")
        if new_type not in ALLOWED_ABSENCE_TYPES:
            raise HTTPException(status_code=400, detail="Недопустимый тип отсутствия")

        # пересечение (кроме себя)
        overlapping = (
            db.query(AbsenceEvent)
            .filter(
                AbsenceEvent.org_id == admin.org_id,
                AbsenceEvent.user_id == row.user_id,
                AbsenceEvent.id != row.id,
                AbsenceEvent.start_at <= new_end,
                AbsenceEvent.end_at >= new_start,
            )
            .first()
        )
        if overlapping:
            raise HTTPException(status_code=400, detail="Уже есть событие в этом периоде для пользователя")

        row.start_at = new_start
        row.end_at = new_end
        row.absence_type = new_type
        db.commit()
        db.refresh(row)

        u = db.query(User).filter(User.id == row.user_id).first()
        return AbsenceOut(
            id=row.id,
            user_id=row.user_id,
            user_login=u.login if u else None,
            user_full_name=u.full_name if u else None,
            start_at=row.start_at,
            end_at=row.end_at,
            absence_type=row.absence_type,
            created_at=row.created_at,
        )

    @app.delete("/api/v1/absence/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_absence(event_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        row = db.query(AbsenceEvent).filter(AbsenceEvent.id == event_id, AbsenceEvent.org_id == admin.org_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        db.delete(row)
        db.commit()
        return None

    # --- productivity rules
    @app.get("/api/v1/productivity/rules", response_model=list[ProductivityRuleOut])
    async def list_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        rows = db.query(ProductivityRule).filter(ProductivityRule.org_id == user.org_id).order_by(ProductivityRule.id.asc()).all()
        return [
            ProductivityRuleOut(
                id=r.id,
                user_id=r.user_id,
                rule_type=r.rule_type,
                pattern=r.pattern,
                is_productive=r.is_productive,
                enabled=r.enabled,
            )
            for r in rows
        ]

    @app.post("/api/v1/productivity/rules", response_model=ProductivityRuleOut, status_code=status.HTTP_201_CREATED)
    async def create_rule(payload: ProductivityRuleCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
        if payload.user_id is not None:
            u = db.query(User).filter(User.id == payload.user_id, User.org_id == admin.org_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
        row = ProductivityRule(
            org_id=admin.org_id,
            user_id=payload.user_id,
            rule_type=payload.rule_type,
            pattern=payload.pattern,
            is_productive=payload.is_productive,
            enabled=payload.enabled,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return ProductivityRuleOut(
            id=row.id,
            user_id=row.user_id,
            rule_type=row.rule_type,
            pattern=row.pattern,
            is_productive=row.is_productive,
            enabled=row.enabled,
        )

    def _daterange(start: date_type, end: date_type):
        cur = start
        while cur <= end:
            yield cur
            cur = cur + timedelta(days=1)

    def _period_bounds(day: date_type):
        month_start = date_type(day.year, day.month, 1)
        if day.month == 12:
            next_month = date_type(day.year + 1, 1, 1)
        else:
            next_month = date_type(day.year, day.month + 1, 1)
        month_end = next_month - timedelta(days=1)
        year_start = date_type(day.year, 1, 1)
        year_end = date_type(day.year, 12, 31)
        return (month_start, month_end), (year_start, year_end)

    def _day_absence_type(db: Session, org_id: int, user_id: int, day: date_type) -> str | None:
        day_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)
        ev = (
            db.query(AbsenceEvent)
            .filter(AbsenceEvent.org_id == org_id, AbsenceEvent.user_id == user_id, AbsenceEvent.start_at <= day_end, AbsenceEvent.end_at >= day_start)
            .first()
        )
        if ev:
            return ev.absence_type
        h = db.query(Holiday).filter(Holiday.org_id == org_id, Holiday.day == day).first()
        return h.kind if h else None

    def _compute_day_from_events(db: Session, org_id: int, user_id: int, day: date_type) -> tuple[list[ActivitySegment], DayMetrics]:
        return compute_day_from_events(db, org_id, user_id, day)

    @app.get("/api/v1/timeline/users", response_model=list[UserOut])
    async def timeline_users(q: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        query = db.query(User).filter(User.org_id == user.org_id, User.is_active.is_(True))
        if q:
            query = query.filter(or_(User.login.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
        rows = query.order_by(User.login.asc()).limit(500).all()
        return [_user_out(u) for u in rows]

    @app.get("/api/v1/timeline/user-activity", response_model=TimelineActivityResponse)
    async def user_activity(
        date: str = Query(..., description="YYYY-MM-DD (UTC in MVP)"),
        user_ids: list[int] = Query(...),
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad date: {e}") from e
        rows = db.query(User).filter(User.org_id == current.org_id, User.id.in_(user_ids)).all()
        users_map = {u.id: u for u in rows}
        activities: list[UserActivity] = []
        for uid in user_ids:
            u = users_map.get(uid)
            if not u:
                continue
            segs, metrics = compute_day_from_events(db, current.org_id, uid, day)
            activities.append(
                UserActivity(
                    user_id=uid,
                    display_name=u.full_name or u.login,
                    segments=segs,
                    metrics=metrics,
                )
            )
        return TimelineActivityResponse(date=date, activities=activities)

    @app.get("/api/v1/timeline/period-stats", response_model=PeriodStatsResponse)
    async def period_stats(
        user_id: int = Query(...),
        date: str = Query(...),
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad date: {e}") from e
        u = db.query(User).filter(User.id == user_id, User.org_id == current.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")

        (m_start, m_end), (y_start, y_end) = _period_bounds(day)

        def _compute_range(start_day: date_type, end_day: date_type, name: str) -> PeriodStats:
            total_days = 0
            weekend_days = 0
            holiday_days = 0
            working_days = 0
            good_days = 0
            medium_days = 0
            bad_days = 0
            absence_days = 0

            for d in _daterange(start_day, end_day):
                total_days += 1
                is_weekend = d.weekday() >= 5
                if is_weekend:
                    weekend_days += 1

                leave_type = _day_absence_type(db, current.org_id, user_id, d)
                if leave_type in ("Праздник", "Выходной"):
                    holiday_days += 1
                    continue
                if is_weekend:
                    continue

                working_days += 1
                if leave_type is not None and leave_type not in ("Праздник", "Выходной"):
                    absence_days += 1
                    continue

                _, metrics = compute_day_from_events(db, current.org_id, user_id, d)
                if metrics.indicator == "blue":
                    absence_days += 1
                elif metrics.indicator == "green":
                    good_days += 1
                elif metrics.indicator == "yellow":
                    medium_days += 1
                else:
                    bad_days += 1

            return PeriodStats(
                period=name,
                start_date=start_day.isoformat(),
                end_date=end_day.isoformat(),
                total_days=total_days,
                weekend_days=weekend_days,
                holiday_days=holiday_days,
                working_days=working_days,
                good_days=good_days,
                medium_days=medium_days,
                bad_days=bad_days,
                absence_days=absence_days,
            )

        month = _compute_range(m_start, m_end, "month")
        year = _compute_range(y_start, y_end, "year")
        return PeriodStatsResponse(user_id=user_id, date=date, month=month, year=year)

    @app.get("/api/v1/media/{media_id}")
    async def download_media(
        media_id: uuid.UUID,
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        mf = db.query(MediaFile).filter(MediaFile.id == media_id, MediaFile.org_id == current.org_id).first()
        if not mf:
            raise HTTPException(status_code=404, detail="Файл не найден")
        path = Path(settings.MEDIA_ROOT) / mf.storage_path
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Файл на диске отсутствует")
        return FileResponse(str(path), media_type=mf.content_type or "image/png")

    @app.get("/api/v1/timeline/day-screenshots", response_model=TimelineDayScreenshotsResponse)
    async def timeline_day_screenshots(
        date: str = Query(..., description="YYYY-MM-DD (UTC)"),
        user_ids: list[int] = Query(...),
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        if not user_ids:
            return TimelineDayScreenshotsResponse(date=date, users=[])
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad date: {e}") from e
        valid = {row[0] for row in db.query(User.id).filter(User.org_id == current.org_id, User.id.in_(user_ids)).all()}
        if not valid:
            return TimelineDayScreenshotsResponse(date=date, users=[])
        day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        rows = (
            db.query(MediaFile, ScreenshotAnalysis, Device.user_id)
            .join(Device, Device.id == MediaFile.device_id)
            .outerjoin(ScreenshotAnalysis, ScreenshotAnalysis.media_file_id == MediaFile.id)
            .filter(
                MediaFile.org_id == current.org_id,
                Device.user_id.in_(valid),
                MediaFile.created_at >= day_start,
                MediaFile.created_at < day_end,
            )
            .order_by(MediaFile.created_at.asc())
            .all()
        )
        by_user: dict[int, list[TimelineScreenshotItemOut]] = defaultdict(list)
        for mf, sa, uid in rows:
            if uid is None:
                continue
            by_user[int(uid)].append(
                TimelineScreenshotItemOut(
                    media_file_id=str(mf.id),
                    created_at=mf.created_at,
                    width=mf.width,
                    height=mf.height,
                    productive_score=sa.productive_score if sa else None,
                    unproductive=sa.unproductive if sa else None,
                    category=sa.category if sa else None,
                    evidence_ru=sa.evidence_ru if sa else None,
                    error_text=sa.error_text if sa else None,
                    analyzed_at=sa.analyzed_at if sa else None,
                )
            )
        users_out = [UserDayScreenshotsOut(user_id=uid, screenshots=items) for uid, items in sorted(by_user.items())]
        return TimelineDayScreenshotsResponse(date=date, users=users_out)

    @app.get("/api/v1/timeline/user-profile", response_model=UserProfileResponse)
    async def timeline_user_profile(
        user_id: int = Query(...),
        days: int = Query(14, ge=1, le=90),
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        u = db.query(User).filter(User.id == user_id, User.org_id == current.org_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        anchor = _utcnow().date()
        recent: list[UserProfileDayRow] = []
        for i in range(days):
            d = anchor - timedelta(days=(days - 1 - i))
            _, m = compute_day_from_events(db, current.org_id, user_id, d)
            recent.append(
                UserProfileDayRow(
                    date=d.isoformat(),
                    kpi_percent=float(m.kpi_percent),
                    indicator=m.indicator,
                    day_fine=int(m.day_fine),
                )
            )
        cutoff = _utcnow() - timedelta(days=30)
        sa_rows = (
            db.query(ScreenshotAnalysis)
            .filter(
                ScreenshotAnalysis.org_id == current.org_id,
                ScreenshotAnalysis.user_id == user_id,
                ScreenshotAnalysis.analyzed_at >= cutoff,
            )
            .all()
        )
        scores = [r.productive_score for r in sa_rows if r.productive_score is not None]
        avg_score = float(sum(scores) / len(scores)) if scores else None
        unprod = sum(1 for r in sa_rows if r.unproductive is True)
        return UserProfileResponse(
            user_id=u.id,
            login=u.login,
            full_name=u.full_name,
            job_title=u.job_title,
            timezone=u.timezone,
            is_active=bool(u.is_active),
            recent_days=recent,
            screenshots_analyzed_30d=len(sa_rows),
            screenshots_avg_score_30d=avg_score,
            screenshots_unproductive_30d=unprod,
        )

    register_extensions(app)
    return app


app = create_app()


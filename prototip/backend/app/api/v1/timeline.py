"""
Модуль Хронология - индивидуальные линейки активности
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta, date as date_type
from app.core.database import get_manictime_db, get_service_db
from app.core.security import get_current_user
from app.models.service_db import AppUser, AppConfiguration, LeaveEvent
from app.schemas.timeline import (
    TimelineActivityResponse,
    TimelinePeriodStatsResponse,
    TimelinePeriodStats,
    TimelineDayMetrics,
    UserActivity,
    ActivitySegment,
    ManicTimeUser,
)

router = APIRouter()

DEFAULT_CFG = {
    "work_timezone": "Europe/Moscow",
    "workday_start": "09:00",
    "workday_end": "18:00",
    "break_start": "13:00",
    "break_end": "14:00",
    "late_penalty_percent": "20",
    "early_leave_penalty_percent": "10",
    "penalty_mode": "binary",  # binary|proportional
}


def _get_cfg(service_db: Session) -> dict:
    keys = list(DEFAULT_CFG.keys())
    items = service_db.query(AppConfiguration).filter(AppConfiguration.key.in_(keys)).all()
    cfg = DEFAULT_CFG.copy()
    for item in items:
        if item.value is not None:
            cfg[item.key] = item.value
    return cfg


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = (value or "").split(":")
    if len(parts) != 2:
        raise ValueError(f"Bad time format: {value}")
    return int(parts[0]), int(parts[1])


def _clip_interval(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> int:
    """Return overlap duration in seconds."""
    if end <= window_start or start >= window_end:
        return 0
    s = max(start, window_start)
    e = min(end, window_end)
    return max(0, int((e - s).total_seconds()))


def _work_windows(cfg: dict, day: date_type) -> tuple[datetime, datetime, datetime, datetime]:
    sh, sm = _parse_hhmm(cfg["workday_start"])
    eh, em = _parse_hhmm(cfg["workday_end"])
    bsh, bsm = _parse_hhmm(cfg["break_start"])
    beh, bem = _parse_hhmm(cfg["break_end"])
    day_start = datetime(day.year, day.month, day.day, sh, sm)
    day_end = datetime(day.year, day.month, day.day, eh, em)
    br_start = datetime(day.year, day.month, day.day, bsh, bsm)
    br_end = datetime(day.year, day.month, day.day, beh, bem)
    return day_start, day_end, br_start, br_end


def _sec_to_min(seconds: int) -> int:
    return int(round(seconds / 60))


def _build_day_metrics(cfg: dict, segments: list[dict], day: date_type) -> TimelineDayMetrics:
    work_start, work_end, br_start, br_end = _work_windows(cfg, day)
    work_seconds = max(0, int((work_end - work_start).total_seconds()))
    break_seconds = _clip_interval(br_start, br_end, work_start, work_end)
    effective_seconds = max(1, work_seconds - break_seconds)

    active_sec = 0
    inactive_sec = 0
    productive_sec = 0

    first_active: Optional[datetime] = None
    last_active: Optional[datetime] = None

    for seg in segments:
        st = datetime.fromisoformat(seg["start"])
        en = datetime.fromisoformat(seg["end"])

        # вычтем обед через два окна: [work_start, br_start) и [br_end, work_end)
        pre = _clip_interval(st, en, work_start, br_start)
        post = _clip_interval(st, en, br_end, work_end)
        dur = pre + post
        if dur <= 0:
            continue

        t = seg["type"]
        if t == "Active":
            active_sec += dur
            # первые/последние точки для опоздал/раньше ушёл считаем по фактическим временам
            if first_active is None or st < first_active:
                first_active = st
            if last_active is None or en > last_active:
                last_active = en
        elif t in ("Away", "Session Locked", "Power Off"):
            inactive_sec += dur
        elif t == "Productive":
            productive_sec += dur

    # нормализация: productive не должен превышать active
    productive_sec = min(productive_sec, active_sec)
    unproductive_sec = max(0, active_sec - productive_sec)

    active_pct = round(active_sec / effective_seconds * 100.0, 2)
    inactive_pct = round(inactive_sec / effective_seconds * 100.0, 2)
    productive_pct = round(productive_sec / effective_seconds * 100.0, 2)
    unproductive_pct = round(unproductive_sec / effective_seconds * 100.0, 2)

    late = False
    early = False
    late_pen = 0.0
    early_pen = 0.0
    mode = (cfg.get("penalty_mode") or "binary").lower()
    late_base = float(cfg.get("late_penalty_percent") or 20)
    early_base = float(cfg.get("early_leave_penalty_percent") or 10)

    if active_sec > 0 and first_active is not None:
        # сравниваем по времени в рамках дня
        if first_active.time() > work_start.time():
            late = True
            if mode == "proportional":
                late_delay = int((datetime(day.year, day.month, day.day, first_active.hour, first_active.minute) - work_start).total_seconds())
                late_pen = round(late_base * min(1.0, max(0.0, late_delay / effective_seconds)), 2)
            else:
                late_pen = round(late_base, 2)

    if active_sec > 0 and last_active is not None:
        if last_active.time() < work_end.time():
            early = True
            if mode == "proportional":
                early_gap = int((work_end - datetime(day.year, day.month, day.day, last_active.hour, last_active.minute)).total_seconds())
                early_pen = round(early_base * min(1.0, max(0.0, early_gap / effective_seconds)), 2)
            else:
                early_pen = round(early_base, 2)

    # KPI по ТЗ
    kpi = round(active_pct + 0.5 * unproductive_pct - late_pen - early_pen, 2)

    if active_sec == 0:
        indicator = "blue"
    elif kpi > 50:
        indicator = "green"
    elif kpi > 30:
        indicator = "yellow"
    else:
        indicator = "red"

    day_fine = 0
    if indicator == "yellow":
        day_fine = -1000
    elif indicator == "red":
        day_fine = -3000

    return TimelineDayMetrics(
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


def _daterange(start: date_type, end: date_type):
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)


def _period_bounds(day: date_type) -> tuple[tuple[date_type, date_type], tuple[date_type, date_type]]:
    month_start = date_type(day.year, day.month, 1)
    if day.month == 12:
        next_month = date_type(day.year + 1, 1, 1)
    else:
        next_month = date_type(day.year, day.month + 1, 1)
    month_end = next_month - timedelta(days=1)

    year_start = date_type(day.year, 1, 1)
    year_end = date_type(day.year, 12, 31)
    return (month_start, month_end), (year_start, year_end)


def _fetch_segments_for_range(manictime_db: Session, user_id: int, start_dt: datetime, end_dt: datetime) -> list[dict]:
    # Важно: используем пересечение по времени, а не только <= end
    query = text(
        """
        SELECT a."Name", a."StartLocalTime", a."EndLocalTime"
        FROM "Ar_Activity" a
        JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
        WHERE t."SchemaName" = 'ManicTime/Computer usage'
          AND t."OwnerId" = :user_id
          AND a."StartLocalTime" < :end_dt
          AND a."EndLocalTime" > :start_dt
        ORDER BY a."StartLocalTime"
        """
    )
    rows = manictime_db.execute(query, {"user_id": user_id, "start_dt": start_dt, "end_dt": end_dt})
    segments: list[dict] = []
    for r in rows:
        segment_type = "Active"
        if r.Name == "Away":
            segment_type = "Away"
        elif r.Name == "Session Locked":
            segment_type = "Session Locked"
        elif r.Name == "Power Off":
            segment_type = "Power Off"
        segments.append({"type": segment_type, "start": r.StartLocalTime.isoformat(), "end": r.EndLocalTime.isoformat()})
    return segments


def _fetch_productive_for_range(manictime_db: Session, user_id: int, start_dt: datetime, end_dt: datetime) -> list[dict]:
    query = text(
        """
        SELECT a."StartLocalTime", a."EndLocalTime"
        FROM "Ar_Activity" a
        JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
        JOIN "Ar_CommonGroup" cg ON a."CommonGroupId" = cg."CommonId"
        JOIN "Ar_CategoryGroup" cag ON cg."CommonId" = cag."CommonGroupId"
        JOIN "Ar_Category" c ON cag."CategoryId" = c."CategoryId"
        WHERE c."Name" = 'Productive'
          AND t."OwnerId" = :user_id
          AND a."StartLocalTime" < :end_dt
          AND a."EndLocalTime" > :start_dt
        ORDER BY a."StartLocalTime"
        """
    )
    rows = manictime_db.execute(query, {"user_id": user_id, "start_dt": start_dt, "end_dt": end_dt})
    return [{"type": "Productive", "start": r.StartLocalTime.isoformat(), "end": r.EndLocalTime.isoformat()} for r in rows]


def _compute_period_stats(
    cfg: dict,
    manictime_db: Session,
    service_db: Session,
    user_id: int,
    start_day: date_type,
    end_day: date_type,
    period_name: str,
) -> TimelinePeriodStats:
    start_dt = datetime(start_day.year, start_day.month, start_day.day, 0, 0, 0)
    end_dt = datetime(end_day.year, end_day.month, end_day.day, 23, 59, 59)

    segments = _fetch_segments_for_range(manictime_db, user_id, start_dt, end_dt)
    segments += _fetch_productive_for_range(manictime_db, user_id, start_dt, end_dt)

    # события отсутствий из служебной БД (datetime) — достаточно для окраски дня
    events = (
        service_db.query(LeaveEvent)
        .filter(
            LeaveEvent.user_id == user_id,
            LeaveEvent.start_date <= datetime(end_day.year, end_day.month, end_day.day, 23, 59, 59),
            LeaveEvent.end_date >= datetime(start_day.year, start_day.month, start_day.day, 0, 0, 0),
        )
        .all()
    )

    event_by_day: dict[date_type, str] = {}
    for ev in events:
        ev_start = ev.start_date.date()
        ev_end = ev.end_date.date()
        for d in _daterange(max(start_day, ev_start), min(end_day, ev_end)):
            event_by_day[d] = ev.leave_type

    # бакетинг сегментов по дню (по StartLocalTime)
    segs_by_day: dict[date_type, list[dict]] = {}
    for s in segments:
        d = datetime.fromisoformat(s["start"]).date()
        if d < start_day or d > end_day:
            continue
        segs_by_day.setdefault(d, []).append(s)

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

        leave_type = event_by_day.get(d)
        if leave_type in ("Праздник", "Выходной"):
            holiday_days += 1
            continue

        if is_weekend:
            continue

        working_days += 1

        if leave_type is not None and leave_type not in ("Праздник", "Выходной"):
            absence_days += 1
            continue

        m = _build_day_metrics(cfg, segs_by_day.get(d, []), d)
        if m.indicator == "blue":
            absence_days += 1
        elif m.indicator == "green":
            good_days += 1
        elif m.indicator == "yellow":
            medium_days += 1
        else:
            bad_days += 1

    return TimelinePeriodStats(
        period=period_name,
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


@router.get("/users", response_model=List[ManicTimeUser])
async def list_manictime_users(
    q: Optional[str] = Query(None, description="Фильтр по имени (подстрока)"),
    limit: int = Query(200, ge=1, le=1000),
    current_user: AppUser = Depends(get_current_user),
    manictime_db: Session = Depends(get_manictime_db),
):
    """
    Список пользователей из ManicTime (для выбора в Хронологии).

    «Чистка»:
    - пропускаем пустые/пробельные DisplayName
    - убираем дубликаты по (DisplayName, UserId) естественно, а по DisplayName — оставляем первый UserId
    """
    users_query = text(
        """
        SELECT "UserId", "DisplayName"
        FROM "Ar_User"
        WHERE "DisplayName" IS NOT NULL
        ORDER BY "DisplayName" ASC
        LIMIT :limit
        """
    )
    rows = manictime_db.execute(users_query, {"limit": limit})

    cleaned: list[ManicTimeUser] = []
    seen_names: set[str] = set()
    q_norm = q.strip().lower() if q else None

    for row in rows:
        name = (row.DisplayName or "").strip()
        if not name:
            continue
        if q_norm and q_norm not in name.lower():
            continue
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        cleaned.append(ManicTimeUser(user_id=row.UserId, display_name=name))

    return cleaned


@router.get("/user-activity", response_model=TimelineActivityResponse)
async def get_user_activity(
    date: str = Query(..., description="Дата (YYYY-MM-DD)"),
    user_ids: List[int] = Query(..., description="Список ID пользователей"),
    current_user: AppUser = Depends(get_current_user),
    manictime_db: Session = Depends(get_manictime_db),
    service_db: Session = Depends(get_service_db),
):
    """
    Получение активности пользователей за указанную дату для построения линеек
    """
    try:
        # Валидация даты
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        date_start_dt = datetime(date_dt.year, date_dt.month, date_dt.day, 0, 0, 0)
        date_end_dt = datetime(date_dt.year, date_dt.month, date_dt.day, 23, 59, 59)
        
        if not user_ids:
            raise HTTPException(status_code=400, detail="Необходимо указать хотя бы одного пользователя")
        
        # Получение информации о пользователях
        users_query = text("""
            SELECT "UserId", "DisplayName"
            FROM "Ar_User"
            WHERE "UserId" = ANY(:user_ids)
        """)
        
        users_result = manictime_db.execute(users_query, {"user_ids": user_ids})
        users_map = {row.UserId: row.DisplayName for row in users_result}
        
        if not users_map:
            raise HTTPException(status_code=404, detail="Пользователи не найдены")
        
        # Получение активности с шкалы Computer usage
        activity_query = text("""
            SELECT
                t."OwnerId",
                a."Name",
                a."StartLocalTime",
                a."EndLocalTime"
            FROM "Ar_Activity" a
            JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
            WHERE t."SchemaName" = 'ManicTime/Computer usage'
              AND t."OwnerId" = ANY(:user_ids)
              AND a."StartLocalTime" < :date_end
              AND a."EndLocalTime" > :date_start
            ORDER BY t."OwnerId", a."StartLocalTime"
        """)
        
        activity_result = manictime_db.execute(
            activity_query,
            {"user_ids": user_ids, "date_start": date_start_dt, "date_end": date_end_dt}
        )
        
        # Получение продуктивного времени
        productive_query = text("""
            SELECT
                t."OwnerId",
                a."StartLocalTime",
                a."EndLocalTime"
            FROM "Ar_Activity" a
            JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
            JOIN "Ar_CommonGroup" cg ON a."CommonGroupId" = cg."CommonId"
            JOIN "Ar_CategoryGroup" cag ON cg."CommonId" = cag."CommonGroupId"
            JOIN "Ar_Category" c ON cag."CategoryId" = c."CategoryId"
            WHERE c."Name" = 'Productive'
              AND t."OwnerId" = ANY(:user_ids)
              AND a."StartLocalTime" < :date_end
              AND a."EndLocalTime" > :date_start
            ORDER BY t."OwnerId", a."StartLocalTime"
        """)
        
        productive_result = manictime_db.execute(
            productive_query,
            {"user_ids": user_ids, "date_start": date_start_dt, "date_end": date_end_dt}
        )
        
        # Группировка по пользователям
        user_activities = {}
        
        for row in activity_result:
            user_id = row.OwnerId
            if user_id not in user_activities:
                user_activities[user_id] = {
                    "user_id": user_id,
                    "display_name": users_map.get(user_id, f"User {user_id}"),
                    "segments": [],
                    "_metrics_segments": [],
                }
            
            # Определение типа сегмента
            segment_type = "Active"
            if row.Name == "Away":
                segment_type = "Away"
            elif row.Name == "Session Locked":
                segment_type = "Session Locked"
            elif row.Name == "Power Off":
                segment_type = "Power Off"
            
            user_activities[user_id]["segments"].append(
                {
                    "type": segment_type,
                    "start": row.StartLocalTime.isoformat(),
                    "end": row.EndLocalTime.isoformat()
                }
            )
            user_activities[user_id]["_metrics_segments"].append(
                {
                    "type": segment_type,
                    "start": row.StartLocalTime.isoformat(),
                    "end": row.EndLocalTime.isoformat(),
                }
            )
        
        # Добавление продуктивного времени
        for row in productive_result:
            user_id = row.OwnerId
            if user_id in user_activities:
                user_activities[user_id]["segments"].append(
                    {
                        "type": "Productive",
                        "start": row.StartLocalTime.isoformat(),
                        "end": row.EndLocalTime.isoformat()
                    }
                )
                user_activities[user_id]["_metrics_segments"].append(
                    {
                        "type": "Productive",
                        "start": row.StartLocalTime.isoformat(),
                        "end": row.EndLocalTime.isoformat(),
                    }
                )
        
        # Формирование ответа
        cfg = _get_cfg(service_db)

        activities = []
        for user_id in user_ids:
            if user_id in user_activities:
                entry = user_activities[user_id]
                metrics = _build_day_metrics(cfg, entry.get("_metrics_segments", []), date_dt.date())
                entry.pop("_metrics_segments", None)
                entry["metrics"] = metrics
                activities.append(UserActivity(**entry))
        
        return TimelineActivityResponse(date=date, activities=activities)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат даты: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")


@router.get("/period-stats", response_model=TimelinePeriodStatsResponse)
async def get_period_stats(
    user_id: int = Query(..., description="ID пользователя ManicTime"),
    date: str = Query(..., description="Опорная дата (YYYY-MM-DD)"),
    current_user: AppUser = Depends(get_current_user),
    manictime_db: Session = Depends(get_manictime_db),
    service_db: Session = Depends(get_service_db),
):
    try:
        date_dt = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат даты: {str(e)}")

    cfg = _get_cfg(service_db)
    (m_start, m_end), (y_start, y_end) = _period_bounds(date_dt)
    month_stats = _compute_period_stats(cfg, manictime_db, service_db, user_id, m_start, m_end, "month")
    year_stats = _compute_period_stats(cfg, manictime_db, service_db, user_id, y_start, y_end, "year")
    return TimelinePeriodStatsResponse(user_id=user_id, date=date, month=month_stats, year=year_stats)

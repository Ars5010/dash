"""
Модуль Сводка - агрегированная гистограмма активности
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date as date_type
from typing import List
from app.core.database import get_manictime_db, get_service_db
from app.core.security import get_current_user
from app.models.service_db import AppUser, LeaveEvent
from app.schemas.summary import SummaryHistogramResponse, SummaryDataset

router = APIRouter()




@router.get("/histogram", response_model=SummaryHistogramResponse)
async def get_summary_histogram(
    start_date: str = Query(..., description="Начальная дата (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Конечная дата (YYYY-MM-DD)"),
    current_user: AppUser = Depends(get_current_user),
    manictime_db: Session = Depends(get_manictime_db),
    service_db: Session = Depends(get_service_db),
):
    """
    Получение данных для гистограммы активности по дням
    """
    try:
        # Валидация дат
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="Начальная дата должна быть раньше конечной")
        
        # SQL запрос для агрегации данных
        query = text("""
            WITH computer_usage AS (
                SELECT
                    a."StartLocalTime",
                    a."EndLocalTime",
                    a."Name",
                    t."OwnerId",
                    DATE_TRUNC('day', a."StartLocalTime") AS "day"
                FROM "Ar_Activity" a
                JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
                WHERE t."SchemaName" = 'ManicTime/Computer usage'
                  AND a."StartLocalTime" >= :start_date
                  AND a."EndLocalTime" <= :end_date
            ),
            productive_time AS (
                SELECT
                    a."StartLocalTime",
                    a."EndLocalTime",
                    t."OwnerId",
                    DATE_TRUNC('day', a."StartLocalTime") AS "day"
                FROM "Ar_Activity" a
                JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
                JOIN "Ar_CommonGroup" cg ON a."CommonGroupId" = cg."CommonId"
                JOIN "Ar_CategoryGroup" cag ON cg."CommonId" = cag."CommonGroupId"
                JOIN "Ar_Category" c ON cag."CategoryId" = c."CategoryId"
                WHERE c."Name" = 'Productive'
                  AND a."StartLocalTime" >= :start_date
                  AND a."EndLocalTime" <= :end_date
            )
            SELECT
                cu."day",
                SUM(CASE WHEN cu."Name" = 'Active' 
                    THEN EXTRACT(EPOCH FROM (cu."EndLocalTime" - cu."StartLocalTime")) 
                    ELSE 0 END) AS active_seconds,
                SUM(CASE WHEN cu."Name" = 'Away' 
                    THEN EXTRACT(EPOCH FROM (cu."EndLocalTime" - cu."StartLocalTime")) 
                    ELSE 0 END) AS away_seconds,
                SUM(CASE WHEN cu."Name" IN ('Session Locked', 'Power Off') 
                    THEN EXTRACT(EPOCH FROM (cu."EndLocalTime" - cu."StartLocalTime")) 
                    ELSE 0 END) AS afk_seconds,
                COALESCE(SUM(EXTRACT(EPOCH FROM (pt."EndLocalTime" - pt."StartLocalTime"))), 0) AS productive_seconds
            FROM computer_usage cu
            LEFT JOIN productive_time pt ON cu."day" = pt."day" 
                AND cu."OwnerId" = pt."OwnerId"
                AND pt."StartLocalTime" < cu."EndLocalTime" 
                AND pt."EndLocalTime" > cu."StartLocalTime"
            GROUP BY cu."day"
            ORDER BY cu."day"
        """)
        
        result = manictime_db.execute(
            query,
            {"start_date": start_date, "end_date": end_date}
        )
        
        rows = result.fetchall()
        
        # Подмешиваем «серые» дни (праздник/выходной) из календаря отсутствий.
        # Это и есть связка «календарь ↔ сводка»: сводка визуально показывает такие дни.
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        leave_events = (
            service_db.query(LeaveEvent)
            .filter(
                LeaveEvent.start_date <= datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59),
                LeaveEvent.end_date >= datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0),
                LeaveEvent.leave_type.in_(["Праздник", "Выходной"]),
            )
            .all()
        )
        gray_days = set()
        for ev in leave_events:
            cur = max(start_dt.date(), ev.start_date.date())
            last = min(end_dt.date(), ev.end_date.date())
            while cur <= last:
                gray_days.add(cur.isoformat())
                cur = date_type.fromordinal(cur.toordinal() + 1)

        # Формирование ответа
        labels = []
        active_data = []
        away_data = []
        afk_data = []
        productive_data = []
        holiday_data = []
        
        for row in rows:
            day = row.day.strftime("%Y-%m-%d")
            labels.append(day)
            active_data.append(float(row.active_seconds or 0))
            away_data.append(float(row.away_seconds or 0))
            afk_data.append(float(row.afk_seconds or 0))
            productive_data.append(float(row.productive_seconds or 0))
            holiday_data.append(0.0)

        # Если «серые» дни есть, добавим отдельный датасет (0 часов, но будет цветной маркер)
        # Проставим небольшую «полоску» 0.01 часа, чтобы бар был видим.
        if gray_days:
            for i, d in enumerate(labels):
                if d in gray_days:
                    holiday_data[i] = 36.0  # 36 секунд ~ 0.01 часа; заметный тонкий столбик
        
        datasets = [
            SummaryDataset(label="Активный", color="green", data=active_data),
            SummaryDataset(label="Неактивный", color="red", data=away_data),
            SummaryDataset(label="Не у ПК", color="yellow", data=afk_data),
            SummaryDataset(label="Продуктивность", color="orange", data=productive_data),
        ]
        if gray_days:
            datasets.append(SummaryDataset(label="Праздник/выходной", color="#6c757d", data=holiday_data))
        
        return SummaryHistogramResponse(labels=labels, datasets=datasets)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат даты: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")


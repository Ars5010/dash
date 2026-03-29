"""
Модуль Метрика - числовые показатели эффективности
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Literal
from app.core.database import get_manictime_db
from app.core.security import get_current_user
from app.models.service_db import AppUser
from app.schemas.metrics import MetricsAggregateResponse, MetricsRow

router = APIRouter()


@router.get("/aggregate", response_model=MetricsAggregateResponse)
async def get_metrics_aggregate(
    period: Literal["week", "month", "quarter", "year"] = Query(..., description="Период агрегации"),
    year: int = Query(..., description="Год"),
    current_user: AppUser = Depends(get_current_user),
    manictime_db: Session = Depends(get_manictime_db)
):
    """
    Получение агрегированных метрик за указанный период
    """
    try:
        if year < 2000 or year > 2100:
            raise HTTPException(status_code=400, detail="Неверный год")
        
        # Определение функции агрегации в зависимости от периода
        date_trunc_func = {
            "week": "week",
            "month": "month",
            "quarter": "quarter",
            "year": "year"
        }.get(period, "quarter")
        
        # SQL запрос для агрегации активного времени
        query = text(f"""
            SELECT
                u."DisplayName" AS user_name,
                DATE_TRUNC('{date_trunc_func}', a."StartLocalTime") AS period_start,
                SUM(EXTRACT(EPOCH FROM (a."EndLocalTime" - a."StartLocalTime"))) AS total_seconds
            FROM "Ar_Activity" a
            JOIN "Ar_Timeline" t ON a."ReportId" = t."ReportId"
            JOIN "Ar_User" u ON t."OwnerId" = u."UserId"
            WHERE
                t."SchemaName" = 'ManicTime/Computer usage'
                AND a."Name" = 'Active'
                AND EXTRACT(YEAR FROM a."StartLocalTime") = :year
            GROUP BY
                u."DisplayName",
                DATE_TRUNC('{date_trunc_func}', a."StartLocalTime")
            ORDER BY
                u."DisplayName",
                period_start
        """)
        
        result = manictime_db.execute(query, {"year": year})
        rows = result.fetchall()
        
        # Группировка данных по пользователям
        user_data = {}
        for row in rows:
            user_name = row.user_name
            if user_name not in user_data:
                user_data[user_name] = {}
            
            # Формирование ключа периода
            period_start = row.period_start
            if period == "week":
                period_key = f"W{period_start.isocalendar()[1]}"
            elif period == "month":
                period_key = f"M{period_start.month}"
            elif period == "quarter":
                quarter = (period_start.month - 1) // 3 + 1
                period_key = f"Q{quarter}"
            else:  # year
                period_key = "Y1"
            
            # Конвертация секунд в часы
            hours = float(row.total_seconds) / 3600
            user_data[user_name][period_key] = round(hours, 2)
        
        # Формирование ответа
        metrics_rows = []
        for user_name, periods in user_data.items():
            metrics_rows.append(MetricsRow(user=user_name, data=periods))
        
        return MetricsAggregateResponse(
            period_type=period,
            year=year,
            data=metrics_rows
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")


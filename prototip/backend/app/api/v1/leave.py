"""
Модуль Отпуска/Больничные
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.core.database import get_service_db
from app.core.security import get_current_user, get_admin_user
from app.models.service_db import AppUser, LeaveEvent
from app.schemas.leave import LeaveEventCreate, LeaveEventResponse

router = APIRouter()

ALLOWED_LEAVE_TYPES = {
    "Отпуск",
    "Больничный",
    "Праздник",
    "Выходной",
    "Прогул",
    "Отгул",
}


@router.get("/events", response_model=List[LeaveEventResponse])
async def get_leave_events(
    start_date: datetime = Query(..., description="Начальная дата-время (ISO)"),
    end_date: datetime = Query(..., description="Конечная дата-время (ISO)"),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_service_db)
):
    """
    Получение списка событий отсутствий за период
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Начальная дата должна быть раньше конечной")
    
    events = db.query(LeaveEvent).filter(
        LeaveEvent.start_date <= end_date,
        LeaveEvent.end_date >= start_date
    ).all()
    
    result = []
    for event in events:
        result.append(LeaveEventResponse(
            id=event.id,
            user_id=event.user_id,
            user_login=event.user.login if event.user else None,
            start_date=event.start_date,
            end_date=event.end_date,
            leave_type=event.leave_type,
            created_at=event.created_at.isoformat() if event.created_at else None
        ))
    
    return result


@router.post("/events", response_model=LeaveEventResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_event(
    event_data: LeaveEventCreate,
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db)
):
    """
    Создание нового события отсутствия (только для администраторов)
    """
    if event_data.start_date > event_data.end_date:
        raise HTTPException(status_code=400, detail="Начальная дата должна быть раньше конечной")

    if event_data.leave_type not in ALLOWED_LEAVE_TYPES:
        raise HTTPException(status_code=400, detail="Недопустимый тип отсутствия")
    
    # Проверка существования пользователя
    user = db.query(AppUser).filter(AppUser.id == event_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверка на пересечение с существующими событиями
    overlapping = db.query(LeaveEvent).filter(
        LeaveEvent.user_id == event_data.user_id,
        LeaveEvent.start_date <= event_data.end_date,
        LeaveEvent.end_date >= event_data.start_date
    ).first()
    
    if overlapping:
        raise HTTPException(
            status_code=400,
            detail="Уже существует событие в этом периоде для данного пользователя"
        )
    
    new_event = LeaveEvent(
        user_id=event_data.user_id,
        start_date=event_data.start_date,
        end_date=event_data.end_date,
        leave_type=event_data.leave_type
    )
    
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    return LeaveEventResponse(
        id=new_event.id,
        user_id=new_event.user_id,
        user_login=new_event.user.login if new_event.user else None,
        start_date=new_event.start_date,
        end_date=new_event.end_date,
        leave_type=new_event.leave_type,
        created_at=new_event.created_at.isoformat() if new_event.created_at else None
    )


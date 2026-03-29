"""
Модуль Панель Администратора
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_service_db
from app.core.security import get_admin_user, get_password_hash
from app.models.service_db import AppUser, AppRole, AppConfiguration
from app.schemas.user import UserCreate, UserResponse
from app.schemas.config import ConfigResponse, ConfigUpdate

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db)
):
    """Получение списка всех пользователей сервиса"""
    users = db.query(AppUser).all()
    result = []
    for user in users:
        result.append(UserResponse(
            id=user.id,
            login=user.login,
            role_id=user.role_id,
            role_name=user.role.role_name if user.role else None,
            is_active=user.is_active,
            created_at=user.created_at
        ))
    return result


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db)
):
    """Создание нового пользователя сервиса"""
    # Проверка существования логина
    existing_user = db.query(AppUser).filter(AppUser.login == user_data.login).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    
    # Проверка существования роли
    role = db.query(AppRole).filter(AppRole.id == user_data.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    
    new_user = AppUser(
        login=user_data.login,
        hashed_password=get_password_hash(user_data.password),
        role_id=user_data.role_id,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        login=new_user.login,
        role_id=new_user.role_id,
        role_name=new_user.role.role_name if new_user.role else None,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@router.get("/config", response_model=List[ConfigResponse])
async def get_config(
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db)
):
    """Получение конфигурации (нечувствительные данные)"""
    config_items = db.query(AppConfiguration).filter(
        AppConfiguration.key.in_(
            ["manictime_host", "manictime_port", "manictime_dbname", "manictime_web_url"]
        )
    ).all()
    
    result = []
    for item in config_items:
        result.append(ConfigResponse(key=item.key, value=item.value))
    
    return result


@router.put("/config", response_model=ConfigResponse)
async def update_config(
    config_data: ConfigUpdate,
    admin_user: AppUser = Depends(get_admin_user),
    db: Session = Depends(get_service_db)
):
    """Обновление конфигурации (нечувствительные данные)"""
    allowed_keys = ["manictime_host", "manictime_port", "manictime_dbname", "manictime_web_url"]
    
    if config_data.key not in allowed_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Ключ '{config_data.key}' не разрешен для редактирования"
        )
    
    config_item = db.query(AppConfiguration).filter(
        AppConfiguration.key == config_data.key
    ).first()
    
    if not config_item:
        config_item = AppConfiguration(key=config_data.key, value=config_data.value)
        db.add(config_item)
    else:
        config_item.value = config_data.value
    
    db.commit()
    db.refresh(config_item)
    
    return ConfigResponse(key=config_item.key, value=config_item.value)


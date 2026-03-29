"""
Модуль аутентификации
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_service_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.models.service_db import AppUser
from app.schemas.auth import LoginRequest, Token

router = APIRouter()


@router.post("/token", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_service_db)
):
    """Аутентификация пользователя и получение JWT токена"""
    user = db.query(AppUser).filter(AppUser.login == login_data.login).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.role_name},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


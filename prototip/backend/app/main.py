"""
Главный модуль FastAPI приложения
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

app = FastAPI(
    title="ManicTime Dashboard API",
    description="API для сервиса дашбордов и аналитики ManicTime",
    version="1.0.0"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "ManicTime Dashboard API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


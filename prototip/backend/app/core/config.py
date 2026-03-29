"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ManicTime Database (Read-Only)
    MANICTIME_DB_HOST: str
    MANICTIME_DB_PORT: int = 5432
    MANICTIME_DB_NAME: str
    MANICTIME_DB_USER: str
    MANICTIME_DB_PASSWORD: str

    # Service Database
    SERVICE_DB_HOST: str
    SERVICE_DB_PORT: int = 5432
    SERVICE_DB_NAME: str
    SERVICE_DB_USER: str
    SERVICE_DB_PASSWORD: str

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


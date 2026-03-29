from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "dev"

    DATABASE_URL: str = "postgresql+psycopg://portal:portal@localhost:5432/portal"

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    TELEGRAM_BOT_TOKEN: str | None = None

    # Локальное хранилище скриншотов (в Docker смонтируйте том на этот путь)
    MEDIA_ROOT: str = "/data/media"

    # Опционально: серверный ИИ (Ollama). Текст: gemma3n:e4b ≈ линейка Google Gemma 3n E4B IT в Ollama.
    OLLAMA_BASE_URL: str | None = None
    OLLAMA_MODEL: str = "gemma3n:e4b"
    # Для анализа скриншотов нужна multimodal-модель (в Ollama у gemma3n:e4b только текст).
    OLLAMA_VISION_MODEL: str = "gemma3:4b-it-q4_K_M"


settings = Settings()


from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class AIProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def summarize_text(self, prompt: str, max_tokens: int = 512) -> str:
        raise NotImplementedError


class StubAIProvider(AIProvider):
    name = "stub"

    async def summarize_text(self, prompt: str, max_tokens: int = 512) -> str:
        return (
            "ИИ отключён или не настроен (stub). Включите ai_enabled для организации и задайте "
            "OLLAMA_BASE_URL для серверного анализа, либо используйте локальный режим на клиенте."
        )


class OllamaAIProvider(AIProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def summarize_text(self, prompt: str, max_tokens: int = 512) -> str:
        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("response") or "").strip() or "(пустой ответ модели)"


def get_ai_provider() -> AIProvider:
    if settings.OLLAMA_BASE_URL:
        return OllamaAIProvider(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
    return StubAIProvider()

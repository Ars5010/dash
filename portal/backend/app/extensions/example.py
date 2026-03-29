"""Пример расширения: отдельный роутер с префиксом /api/v1/ext/example."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/ext/example", tags=["extension-example"])


@router.get("/ping")
async def example_ping() -> dict[str, str]:
    return {"module": "example", "ok": "true"}

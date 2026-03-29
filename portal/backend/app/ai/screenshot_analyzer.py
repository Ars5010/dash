"""Вызов vision-модели Ollama и разбор ответа."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.screenshot_prompts import (
    SCREENSHOT_UNPRODUCTIVITY_SYSTEM,
    build_activity_context_lines,
    build_user_prompt,
)
from app.core.config import settings

if TYPE_CHECKING:
    from app.models import MediaFile, ScreenshotAnalysis


def _extract_json_object(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {
        "productive_score": 0,
        "category": "unknown",
        "unproductive": True,
        "concerns": ["parse_error"],
        "evidence_ru": "Не удалось разобрать ответ модели.",
    }


async def analyze_screenshot_file(
    *,
    image_path: Path,
    activity_titles: list[tuple[str, str | None]],
    timeout: float = 180.0,
) -> tuple[dict[str, Any], str, str]:
    """
    Возвращает (parsed_json, raw_model_text, vision_model_used).
    """
    if not settings.OLLAMA_BASE_URL:
        raise RuntimeError("OLLAMA_BASE_URL не задан")
    vision_model = settings.OLLAMA_VISION_MODEL
    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    ctx = build_activity_context_lines(activity_titles)
    user_text = build_user_prompt(ctx)
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload: dict[str, Any] = {
        "model": vision_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SCREENSHOT_UNPRODUCTIVITY_SYSTEM},
            {
                "role": "user",
                "content": user_text,
                "images": [b64],
            },
        ],
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        body = r.json()
    msg = body.get("message") or {}
    raw = (msg.get("content") or "").strip()
    parsed = _extract_json_object(raw)
    # нормализация типов
    try:
        ps = int(parsed.get("productive_score", 0))
        parsed["productive_score"] = max(0, min(100, ps))
    except (TypeError, ValueError):
        parsed["productive_score"] = 0
    parsed["unproductive"] = bool(parsed.get("unproductive", parsed["productive_score"] < 45))
    if not isinstance(parsed.get("concerns"), list):
        parsed["concerns"] = []
    parsed["evidence_ru"] = str(parsed.get("evidence_ru") or "")[:2000]
    parsed["category"] = str(parsed.get("category") or "unknown")[:32]
    return parsed, raw, vision_model


def collect_window_titles_for_device(db: Session, device_id: int, limit: int = 12) -> list[tuple[str, str | None]]:
    from app.models import ActivityEvent

    rows = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.device_id == device_id, ActivityEvent.type == "window")
        .order_by(ActivityEvent.ts.desc())
        .limit(limit)
        .all()
    )
    titles: list[tuple[str, str | None]] = []
    for ev in reversed(rows):
        d = ev.data or {}
        titles.append((str(d.get("app") or ""), d.get("title")))
    return titles


async def persist_screenshot_analysis(db: Session, mf: "MediaFile") -> "ScreenshotAnalysis":
    """
    Создаёт строку screenshot_analyses (успех или ошибка). Если запись уже есть — возвращает её без повторного вызова модели.
    """
    from app.models import Device, ScreenshotAnalysis

    existing = db.query(ScreenshotAnalysis).filter(ScreenshotAnalysis.media_file_id == mf.id).first()
    if existing:
        return existing

    dev = db.query(Device).filter(Device.id == mf.device_id).first()
    uid = dev.user_id if dev else None
    path = Path(settings.MEDIA_ROOT) / mf.storage_path

    if not path.is_file():
        row = ScreenshotAnalysis(
            media_file_id=mf.id,
            org_id=mf.org_id,
            user_id=uid,
            device_id=mf.device_id,
            productive_score=None,
            category="missing_file",
            unproductive=None,
            concerns=[],
            evidence_ru=None,
            vision_model=None,
            raw_model_text=None,
            error_text="Файл на сервере отсутствует",
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return db.query(ScreenshotAnalysis).filter(ScreenshotAnalysis.media_file_id == mf.id).one()
        db.refresh(row)
        return row

    titles = collect_window_titles_for_device(db, mf.device_id)
    try:
        parsed, raw, vm = await analyze_screenshot_file(image_path=path, activity_titles=titles)
        row = ScreenshotAnalysis(
            media_file_id=mf.id,
            org_id=mf.org_id,
            user_id=uid,
            device_id=mf.device_id,
            productive_score=int(parsed.get("productive_score", 0)),
            category=str(parsed.get("category", "unknown")),
            unproductive=bool(parsed.get("unproductive")),
            concerns=[str(x) for x in (parsed.get("concerns") or [])][:50],
            evidence_ru=str(parsed.get("evidence_ru", "")),
            vision_model=vm,
            raw_model_text=raw[:16000] if raw else None,
            error_text=None,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return db.query(ScreenshotAnalysis).filter(ScreenshotAnalysis.media_file_id == mf.id).one()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        err = str(e)[:4000]
        row = ScreenshotAnalysis(
            media_file_id=mf.id,
            org_id=mf.org_id,
            user_id=uid,
            device_id=mf.device_id,
            productive_score=None,
            category="error",
            unproductive=None,
            concerns=[],
            evidence_ru=None,
            vision_model=settings.OLLAMA_VISION_MODEL,
            raw_model_text=None,
            error_text=err,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return db.query(ScreenshotAnalysis).filter(ScreenshotAnalysis.media_file_id == mf.id).one()
        db.refresh(row)
        return row

"""Распаковка gzip-тела запроса до разбора JSON (совместимо с aw-portal-uploader)."""

from __future__ import annotations

import gzip

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _scope_with_body_headers(scope: dict, body: bytes) -> dict:
    """Убираем chunked/gzip и выставляем content-length = len(body), иначе Starlette/FastAPI ломают разбор JSON."""
    scope = dict(scope)
    h: list[tuple[bytes, bytes]] = []
    for k, v in scope.get("headers", []):
        kl = k.lower()
        if kl in (b"content-encoding", b"content-length", b"transfer-encoding"):
            continue
        h.append((k, v))
    h.append((b"content-length", str(len(body)).encode()))
    scope["headers"] = h
    return scope


class GzipRequestBodyMiddleware(BaseHTTPMiddleware):
    """Content-Encoding: gzip → распаковка; для /ingest/batch — ещё и gzip без заголовка (прокси снял encoding)."""

    async def dispatch(self, request: Request, call_next):
        enc = (request.headers.get("content-encoding") or "").lower().strip()
        method = request.method.upper()
        path = request.url.path or ""
        ingest_batch = method in ("POST", "PUT", "PATCH") and "/api/v1/ingest/batch" in path

        if enc == "gzip":
            raw = await request.body()
            if not raw:
                return await call_next(request)
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return Response(
                    status_code=400,
                    content='{"detail":"Invalid gzip body"}',
                    media_type="application/json",
                )
            return await _forward_raw_body(request, raw, call_next)

        if ingest_batch:
            raw = await request.body()
            if not raw:
                return await call_next(request)
            if len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B:
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    return Response(
                        status_code=400,
                        content='{"detail":"Invalid gzip body"}',
                        media_type="application/json",
                    )
            return await _forward_raw_body(request, raw, call_next)

        return await call_next(request)


async def _forward_raw_body(request: Request, raw: bytes, call_next):
    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    scope = _scope_with_body_headers(request.scope, raw)
    new_request = Request(scope, receive)
    return await call_next(new_request)

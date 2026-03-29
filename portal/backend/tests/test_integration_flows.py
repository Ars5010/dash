from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("PORTAL_INTEGRATION_TESTS"),
    reason="Полный цикл: PORTAL_INTEGRATION_TESTS=1 и поднятая БД с миграциями",
)


def test_bootstrap_enroll_ingest_screenshot(client):
    """Один проход: bootstrap → ключ установки → enroll-with-user → ingest → скрин (если включено)."""
    org_name = f"TestOrg_{uuid.uuid4().hex[:8]}"
    login = f"adm_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/v1/admin/bootstrap",
        json={
            "org_name": org_name,
            "login": login,
            "password": "secret123",
            "full_name": "Admin",
            "job_title": "CTO",
            "timezone": "Europe/Moscow",
            "role": "admin",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["id"] > 0

    tok = client.post("/api/v1/auth/token", json={"login": login, "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    org_id = client.get("/api/v1/meta/me", headers=headers).json()["org_id"]

    s = client.patch(
        "/api/v1/admin/org/settings",
        headers=headers,
        json={"self_registration_enabled": True, "screenshots_enabled": True, "ai_enabled": False},
    )
    assert s.status_code == 200, s.text

    sec = client.post("/api/v1/admin/org/install-secret", headers=headers)
    assert sec.status_code == 200, sec.text
    install_secret = sec.json()["install_secret"]

    ul = f"user_{uuid.uuid4().hex[:8]}"
    dev = f"dev_{uuid.uuid4().hex[:8]}"
    enr = client.post(
        "/api/v1/devices/enroll-with-user",
        json={
            "org_id": org_id,
            "install_secret": install_secret,
            "login": ul,
            "password": "userpass123",
            "full_name": "Тест Пользователь",
            "job_title": "Менеджер",
            "timezone": "Europe/Moscow",
            "device_id": dev,
            "hostname": "pytest-host",
            "os": "nt",
        },
    )
    assert enr.status_code == 201, enr.text
    device_token = enr.json()["token"]
    dh = {"Authorization": f"Bearer {device_token}"}

    pol = client.get("/api/v1/devices/policy", headers=dh)
    assert pol.status_code == 200
    assert pol.json().get("screenshots_enabled") is True

    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up = client.post(
        "/api/v1/devices/screenshots",
        headers=dh,
        files={"file": ("x.png", tiny_png, "image/png")},
    )
    assert up.status_code == 200, up.text
    media_id = up.json()["media_id"]

    ing = client.post(
        "/api/v1/ingest/batch",
        headers=dh,
        json={
            "device_id": dev,
            "sent_at": "2026-03-29T12:00:00+00:00",
            "events": [
                {
                    "seq": 1,
                    "type": "screenshot",
                    "ts": "2026-03-29T12:00:00+00:00",
                    "data": {"media_id": media_id},
                }
            ],
        },
    )
    assert ing.status_code == 200, ing.text
    assert ing.json().get("accepted") == 1

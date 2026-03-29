from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest
from sqlalchemy import create_engine, text

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")

_DEFAULT_DB = "postgresql+psycopg://portal:portal@127.0.0.1:5432/portal"


def _database_reachable(url: str) -> bool:
    try:
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
def client():
    url = os.environ.get("DATABASE_URL", _DEFAULT_DB)
    if not _database_reachable(url):
        pytest.skip("PostgreSQL недоступен по DATABASE_URL (например `docker compose up -d db backend`)")
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

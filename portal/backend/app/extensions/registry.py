"""Регистрация дополнительных модулей портала.

Добавьте свой модуль:
1) Создайте `app/extensions/my_module.py` с `router = APIRouter(...)`
2) Импортируйте и вызовите `app.include_router(my_module.router)` ниже.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.extensions import example


def register_extensions(app: FastAPI) -> None:
    app.include_router(example.router)

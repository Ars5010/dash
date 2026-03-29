"""Подключение расширений агента.

Добавьте импорт своего модуля и вызов хуков в `run_sync_hooks`.
"""

from __future__ import annotations

from typing import Any

from aw_portal_uploader.extensions import example as example_ext

_HOOKS: list[Any] = [example_ext.on_sync_tick]


def run_sync_hooks(ctx: dict) -> None:
    for fn in _HOOKS:
        try:
            fn(ctx)
        except Exception:
            pass

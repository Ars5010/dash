"""Захват экрана (Windows/Linux/macOS через mss)."""

from __future__ import annotations

import io
from typing import Optional


def capture_screen_png() -> Optional[bytes]:
    try:
        import mss
        import mss.tools
    except ImportError:
        return None
    try:
        with mss.mss() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(mon)
        buf = io.BytesIO()
        mss.tools.to_png(shot.rgb, shot.size, output=buf)
        return buf.getvalue()
    except Exception:
        return None

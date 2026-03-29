from __future__ import annotations

import httpx


async def tg_send_message(*, bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
        resp.raise_for_status()


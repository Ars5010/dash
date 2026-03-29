"""Промпты для оценки непродуктивности по скриншоту рабочего стола.

Модель должна вернуть строгий JSON (без markdown), чтобы его можно было разобрать в коде.
"""

from __future__ import annotations

# Системный контекст: снижает выдумывание, задаёт шкалу и этику.
SCREENSHOT_UNPRODUCTIVITY_SYSTEM = """Ты аналитик рабочей активности. Тебе дают снимок экрана сотрудника (может быть частично нечитаемым).
Правила:
- Описывай ТОЛЬКО то, что реально видно на изображении. Не придумывай окна, сайты и приложения, если их не видно.
- Не делай выводов о личных качествах человека; только о видимой активности на экране.
- «Продуктивно» = видимые рабочие инструменты: документы, почта/мессенджеры по работе, IDE, таблицы, CRM, терминал с кодом, обучающие материалы по задаче.
- «Непродуктивно» = явно досуг: игры, стримы, развлекательные видео, лента соцсетей, шопинг не по работе, мемы — если это явно видно.
- Если смешанный или неоднозначный контент — score ближе к середине и category=mixed или unknown.
Ответ СТРОГО одним JSON-объектом на русском языке в полях evidence_ru и concerns, без текста до или после JSON."""

SCREENSHOT_UNPRODUCTIVITY_USER_TEMPLATE = """Оцени продуктивность текущего скрина для рабочего контекста.

Контекст из телеметрии (последние заголовки окон / приложений, может быть пусто):
{activity_context}

Верни один JSON со схемой:
{{
  "productive_score": <целое 0-100, где 100 максимально продуктивно>,
  "category": "work" | "entertainment" | "communication" | "mixed" | "unknown",
  "unproductive": <true если score < 45 или явный досуг>,
  "concerns": [<краткие строки-флаги, напр. "видео YouTube", "игра">],
  "evidence_ru": "<1-3 предложения: что видно и почему такая оценка>"
}}
Только JSON, без markdown."""


def build_activity_context_lines(titles_apps: list[tuple[str, str | None]]) -> str:
    if not titles_apps:
        return "(нет данных ActivityWatch)"
    lines = []
    for app, title in titles_apps[:15]:
        t = (title or "").strip()[:200]
        a = (app or "").strip()[:80]
        lines.append(f"- {a}: {t}" if t else f"- {a}")
    return "\n".join(lines)


def build_user_prompt(activity_context_block: str) -> str:
    return SCREENSHOT_UNPRODUCTIVITY_USER_TEMPLATE.format(activity_context=activity_context_block)

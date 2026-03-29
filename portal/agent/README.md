# Агент (ActivityWatch uploader)

Этот компонент ставится **на ПК сотрудника** и отправляет события из локального ActivityWatch (`aw-server`) в портал.

## Состав «инсталлятора» (что должно оказаться на ПК)
- **ActivityWatch**:
  - `aw-server` (локальная база событий)
  - watchers:
    - `aw-watcher-window` (активное окно / приложение)
    - `aw-watcher-afk` (AFK/не AFK + duration)
    - опционально `aw-watcher-web` (URL/host/title) — обычно через расширение браузера
- **Наш uploader**: `aw-portal-uploader` (этот проект)
  - периодически читает события из локального `aw-server`
  - нормализует их
  - отправляет в портал батчами

## Первый запуск (enrollment)
1) Админ в портале создаёт **одноразовый enrollment code**:\n
- `POST /api/v1/devices/enrollment-codes`\n

2) На ПК запускается uploader. Если токена ещё нет — он попросит enrollment code и выполнит enrollment:\n
- `POST /api/v1/devices/enroll` → получает `device_token`\n

3) Токен сохраняется локально в state-файл:\n
- Linux: `~/.local/state/activitywatch-portal/uploader_state.json`\n
- Windows: обычно `ProgramData\\ActivityWatchPortal\\uploader_state.json`\n

Дальше uploader использует `device_token` в `Authorization: Bearer ...` для ingest.

## Политика приватности URL
Uploader перед каждой синхронизацией запрашивает политику:\n
- `GET /api/v1/devices/policy`

Параметры:\n
- `url_policy_mode`:\n
  - `full` — отправляем полный `url` и `host`\n
  - `host_only` — отправляем только `host`\n
  - `drop` — если домен запрещён, URL не отправляем вообще\n
- `allow_domains` — белый список доменов (если задан, пропускаются только они)\n
- `deny_domains` — чёрный список доменов\n

Важная деталь: домены сопоставляются по правилу `example.com` покрывает `sub.example.com`.

## Частота синхронизации
Из политики берётся `sync_interval_seconds`.\n
Ограничения:\n
- минимум 30 сек\n
- максимум 3600 сек\n

Также можно ограничить размер батча переменной:\n
- `AW_PORTAL_MAX_EVENTS_PER_SYNC` (default: 2000)

## Устойчивость (backoff, идемпотентность)
- **Backoff**: при любой ошибке uploader ждёт 1s → 2s → 4s … максимум 300s и повторяет цикл.
- **Идемпотентность**: каждый отправленный эвент имеет `seq` (монотонный счётчик), а портал сохраняет уникальность по `(device_id, seq)`. Повторная отправка того же `seq` не портит данные.
- **Курсоры бакетов**: uploader хранит `bucket_cursors` (последний ISO timestamp по каждому bucket) в state-файле, чтобы не перечитывать всё с нуля.

## Запуск (пример)

```bash
python -m aw_portal_uploader --portal-url "http://<PORTAL>:8000" --aw-server-url "http://127.0.0.1:5600" --enrollment-code "<CODE>"
```

Переменные окружения (альтернатива флагам):\n
- `AW_PORTAL_URL`\n
- `AW_SERVER_URL`\n
- `AW_PORTAL_ENROLLMENT_CODE`\n
- `AW_PORTAL_DEVICE_ID`\n
- `AW_PORTAL_STATE_DIR`\n


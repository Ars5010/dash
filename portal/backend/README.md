# Backend (FastAPI)

## Назначение
Backend принимает события ActivityWatch от устройств (device token), хранит их в Postgres и отдаёт API для портала (JWT). Также умеет отправлять отчёты в Telegram.

## Авторизация: user JWT vs device token
- **User JWT** (люди в веб-портале):\n
  - Получение токена: `POST /api/v1/auth/token`\n
  - Использование: `Authorization: Bearer <JWT>`\n
  - Доступ: все UI-эндпоинты (`/timeline/*`, `/absence/*`, `/productivity/*`, `/admin/*`, `/telegram/*`)\n
- **Device token** (агенты на ПК):\n
  - Получение токена: `POST /api/v1/devices/enroll` по одноразовому enrollment code\n
  - Использование: `Authorization: Bearer <DEVICE_TOKEN>`\n
  - Доступ: ingestion эндпоинт `POST /api/v1/ingest/batch` и `GET /api/v1/devices/policy`\n

## Эндпоинты (MVP)
### Bootstrap/Users
- `POST /api/v1/admin/bootstrap` — одноразовое создание организации + admin пользователя
- `GET /api/v1/admin/users` — список пользователей (admin)

### Auth
- `POST /api/v1/auth/token` — JWT по логину/паролю

### Devices
- `POST /api/v1/devices/enrollment-codes` — создать enrollment code (admin)
- `POST /api/v1/devices/enroll` — enrollment устройства, выдаёт device token
- `GET /api/v1/devices/policy` — политика приватности URL + интервал синхронизации

### Ingest
- `POST /api/v1/ingest/batch` — приём батча событий\n
  - **идемпотентность**: уникальность `(device_id, seq)`; повторная отправка того же `seq` безопасна

### Productivity rules
- `GET /api/v1/productivity/rules` — список правил
- `POST /api/v1/productivity/rules` — создать правило (admin)

### Absence
- `GET /api/v1/absence/events?start_at=...&end_at=...` — список отсутствий
- `POST /api/v1/absence/events` — создать отсутствие (admin)

### Timeline
- `GET /api/v1/timeline/users?q=...` — список пользователей для выбора
- `GET /api/v1/timeline/user-activity?date=YYYY-MM-DD&user_ids=...` — сегменты дня + метрики справа\n
  - расчёт метрик использует события `aw-watcher-afk` (active/inactive) и правила продуктивности поверх window/web\n
- `GET /api/v1/timeline/period-stats?user_id=...&date=...` — показатели за месяц/год

### Telegram
- `GET /api/v1/telegram/subscriptions` — список чатов (admin)
- `POST /api/v1/telegram/subscriptions` — добавить чат (admin)
- `POST /api/v1/telegram/send-daily-report?date=YYYY-MM-DD` — ручной запуск дневного отчёта (admin)

## Миграции Postgres (Alembic)
Файлы:\n
- `alembic.ini`\n
- `alembic/env.py`\n
- `alembic/versions/*`\n

Команды (локально):\n
```bash
cd portal/backend
alembic upgrade head
```\n

## Фоновые джобы
Используем **APScheduler** (AsyncIO scheduler), стартует при запуске приложения.\n
Текущий job:\n
- `tg_daily_report` — отправка отчёта в Telegram раз в день (MVP: 09:00 UTC)\n

Файлы:\n
- `app/scheduler.py`\n
- `app/jobs.py`\n

## Запуск в Docker
Из корня `portal/`:\n
```bash
docker compose up --build
```\n

После старта:\n
- API: `http://localhost:8000`\n
- Swagger: `http://localhost:8000/docs`\n


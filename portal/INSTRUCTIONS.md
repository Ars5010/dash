# Инструкция: Portal + ActivityWatch (базовый клиент)

## 1) Запуск сервера (Portal)

### Вариант A: Docker (рекомендуется)

Из папки `portal/`:

```bash
docker compose up --build
```

После старта:
- **Портал (веб + API через nginx)**: `http://localhost:8010` — откройте в браузере `/setup`, `/login` и т.д.
- **API напрямую (без nginx)**: `http://localhost:8011` — для отладки или если подняли только `db` + `backend`
- **Health**: `GET http://localhost:8010/api/health` или `http://localhost:8011/api/health`

Сервисы: `web` (React), `backend` (FastAPI), `db` (PostgreSQL). Раньше в compose был только backend — интерфейс шёл отдельной командой `npm run dev` в `frontend/`.

### Первый запуск (bootstrap)
Откройте `http://localhost:8010/setup` и создайте организацию + admin (делается один раз).

Если видите **Already bootstrapped** — в базе уже есть пользователи: используйте **`/login`**, либо сбросьте данные для «новой» установки: из каталога `portal/` выполните `docker compose down -v`, затем снова `docker compose up --build` (том PostgreSQL удалится вместе с данными).

Далее вход: `http://localhost:8010/login` — используйте **тот же** логин и пароль, что указали на `/setup` (значения «admin» / «admin123» в форме только пример).

Если пароль забыли или `/setup` проходили с другим паролем, сброс из контейнера:
`docker compose exec backend python /app/scripts/reset_user_password.py <логин> <новый_пароль>`

## 2) Выдача токена для ПК (через админку)

1) В портале зайдите в **Админка** → блок **Enrollment code**.
2) (Опционально) выберите пользователя — тогда ПК закрепится за ним.
3) Создайте code и скопируйте команду подключения.

## 3) Что поставить на ПК сотрудника (ActivityWatch)

### Минимум
- `aw-server`
- `aw-watcher-window`
- `aw-watcher-afk`

### Опционально (для сайтов)
- `aw-watcher-web` (обычно через расширение браузера ActivityWatch)

Проверка, что локальный ActivityWatch работает:
- `http://127.0.0.1:5600` открывается в браузере на ПК

## 4) Подключение ПК к порталу (uploader)

Uploader читает события из локального `aw-server` и отправляет их в портал батчами.

Есть два способа запуска.

### Вариант A: без EXE (Python)

На ПК должен быть Python 3.10+.

1) Скопируйте папку `portal/agent` на ПК (или возьмите её из репозитория).
2) В папке `agent`:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или: .\.venv\Scripts\activate  # Windows PowerShell
pip install -r requirements.txt
python -m aw_portal_uploader --portal-url "http://<PORTAL_HOST>:8010" --aw-server-url "http://127.0.0.1:5600" --enrollment-code "<CODE>"
```

### Вариант B: EXE (Windows)

Смотрите `portal/agent/build_windows_exe.md`.

Команда запуска (пример):

```powershell
.\aw-portal-uploader.exe --portal-url "http://<PORTAL_HOST>:8010" --aw-server-url "http://127.0.0.1:5600" --enrollment-code "<CODE>"
```

## 5) Проверка, что данные пошли

В портале: **Админка → Устройства и токены**
- **Последнее событие** должно обновляться
- При необходимости можно **Отозвать** устройство (это остановит отправку данных)

## 6) Где лежит токен/состояние uploader

Uploader сохраняет состояние в `uploader_state.json`:
- **Windows**: обычно `%ProgramData%\ActivityWatchPortal\uploader_state.json`
- **Linux**: `~/.local/state/activitywatch-portal/uploader_state.json`

## 7) Типовые проблемы

- **401 Invalid device token / Device revoked**: устройство отозвано или токен неверный → сделайте новый enrollment code и переподключите.
- **Network error**: проверьте доступность `http://<PORTAL_HOST>:8010/api/health` с ПК.
- **Нет событий**: проверьте, что на ПК запущены `aw-server` и watchers.


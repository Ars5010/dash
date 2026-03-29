## Windows агент: как получить EXE и подключить ПК

### 1) Собрать EXE (самый простой способ)

В репозиторий добавлен GitHub Actions workflow: `Build Windows Agent Installer`.

1. Откройте Actions → `Build Windows Agent Installer`
2. Нажмите **Run workflow**
3. Дождитесь окончания
4. Скачайте artifact `windows-agent-installer` — там будет `activitywatch-...-setup.exe`

Этот инсталлятор включает:
- `aw-qt` (локальный UI)
- `aw-server` (локальный сервер данных ActivityWatch)
- watchers (window/afk)
- `aw-portal-uploader.exe` (отправка в портал)

### 2) Подготовить портал (сервер) и enrollment code

На сервере (Docker) создайте enrollment code (через админ JWT):
- `POST /api/v1/devices/enrollment-codes`

### 3) Установка на Windows

1. Запустите `activitywatch-...-setup.exe`
2. После установки запустится `aw-qt` и `aw-portal-uploader.exe`
3. Первый запуск uploader попросит enrollment code (если не задан через env/параметры)

Параметры uploader (если нужно вручную):

```powershell
aw-portal-uploader.exe --portal-url "http://<SERVER_IP>:8010" --enrollment-code "<CODE>" --device-id "<PCNAME>"
```

### 4) Web watcher (веб‑сайты)

В MVP веб‑трекер требует расширение `aw-watcher-web` (автоустановка возможна только через enterprise policies).
См. `docs/activitywatch-web-watcher.md`.


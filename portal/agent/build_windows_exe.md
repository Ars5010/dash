# Сборка `aw-portal-uploader.exe` (Windows)

## Вариант 1: собрать на Windows (самый простой)
1) Установить Python 3.10+\n
2) В папке `portal/agent`:\n
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --onefile --name aw-portal-uploader --collect-all requests -m aw_portal_uploader
```\n
Готовый файл будет в `dist\\aw-portal-uploader.exe`.

## Вариант 2: CI (GitHub Actions)
Следующий шаг — добавить workflow как в `prototip/.github/workflows/build-windows-agent.yml`:\n
- сборка exe\n
- публикация artifact\n

## Мастер регистрации (логин/пароль/ФИО + ключ установки из админки)
```powershell
.\aw-portal-uploader.exe --install-wizard
```
или `aw-portal-install-wizard.exe` при сборке с entry point `aw-portal-install-wizard`.

## Проверка на ПК
```powershell
.\aw-portal-uploader.exe --portal-url "http://<PORTAL>:8010" --aw-server-url "http://127.0.0.1:5600" --enrollment-code "PC-001"
```


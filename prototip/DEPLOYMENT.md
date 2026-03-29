# Инструкция по развертыванию

## Быстрый старт

### 1. Подготовка окружения

#### Установка зависимостей системы

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.9 python3-pip python3-venv postgresql-client nodejs npm
```

**Windows:**
- Установите Python 3.9+ с официального сайта
- Установите Node.js 18+ с официального сайта
- Установите PostgreSQL с официального сайта

### 2. Настройка баз данных

#### Создание readonly роли для ManicTime БД

**ВАЖНО**: Выполните эти команды на сервере PostgreSQL, где находится база данных ManicTime:

```sql
-- Подключитесь к PostgreSQL как суперпользователь
psql -U postgres

-- Создайте роль
CREATE ROLE manictime_readonly LOGIN PASSWORD 'N0v1y_S3cur3_P@ssw0rd!';

-- Предоставьте права на подключение к БД
GRANT CONNECT ON DATABASE "ManicTimeReports" TO manictime_readonly;

-- Предоставьте права на схему
GRANT USAGE ON SCHEMA public TO manictime_readonly;

-- Предоставьте права на чтение таблиц
GRANT SELECT ON ALL TABLES IN SCHEMA public TO manictime_readonly;

-- Для новых таблиц (если они будут созданы)
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO manictime_readonly;
```

#### Создание служебной базы данных

```sql
CREATE DATABASE dashboard_service;
```

### 3. Настройка Backend

```bash
cd backend

# Создание виртуального окружения
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Создание файла .env
cp .env.example .env

# Отредактируйте .env с вашими настройками
# Используйте любой текстовый редактор
```

#### Настройка .env файла

Откройте `backend/.env` и заполните следующие параметры:

```env
# ManicTime Database (Read-Only)
MANICTIME_DB_HOST=192.168.1.100  # IP или hostname сервера ManicTime БД
MANICTIME_DB_PORT=5432
MANICTIME_DB_NAME=ManicTimeReports
MANICTIME_DB_USER=manictime_readonly
MANICTIME_DB_PASSWORD=N0v1y_S3cur3_P@ssw0rd!  # Пароль, который вы установили выше

# Service Database
SERVICE_DB_HOST=localhost
SERVICE_DB_PORT=5432
SERVICE_DB_NAME=dashboard_service
SERVICE_DB_USER=postgres
SERVICE_DB_PASSWORD=ваш_пароль_postgres

# JWT Settings
JWT_SECRET_KEY=$(openssl rand -hex 32)  # Сгенерируйте случайный ключ
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Для генерации JWT_SECRET_KEY на Linux/Mac:**
```bash
openssl rand -hex 32
```

**Для Windows:**
Используйте онлайн генератор или Python:
```python
import secrets
print(secrets.token_hex(32))
```

#### Инициализация базы данных

```bash
# Применение миграций
alembic upgrade head

# Создание начальных ролей и администратора
python scripts/init_db.py
```

### 4. Запуск Backend

```bash
# Режим разработки
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или для production (рекомендуется использовать gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Backend будет доступен по адресу: `http://localhost:8000`

API документация: `http://localhost:8000/docs`

### 5. Настройка Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск в режиме разработки
npm run dev

# Или сборка для production
npm run build
```

Frontend будет доступен по адресу: `http://localhost:3000`

### 6. Первый вход

После успешного запуска:

1. Откройте браузер и перейдите на `http://localhost:3000`
2. Вы увидите страницу входа
3. Используйте учетные данные:
   - **Логин**: `admin`
   - **Пароль**: `admin123`
4. После входа **НЕМЕДЛЕННО** измените пароль через панель администратора

## Развертывание в Production

### Использование Docker

```bash
# Создайте .env файл в корне проекта
cp backend/.env.example .env

# Отредактируйте .env

# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Настройка Nginx (рекомендуется)

Пример конфигурации Nginx для production:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service (для Linux)

Создайте файл `/etc/systemd/system/manictime-dashboard.service`:

```ini
[Unit]
Description=ManicTime Dashboard Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/dash/backend
Environment="PATH=/path/to/dash/backend/venv/bin"
ExecStart=/path/to/dash/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Активация сервиса:

```bash
sudo systemctl daemon-reload
sudo systemctl enable manictime-dashboard
sudo systemctl start manictime-dashboard
sudo systemctl status manictime-dashboard
```

## Устранение неполадок

### Проблема: Не удается подключиться к БД ManicTime

**Решение:**
1. Проверьте, что роль `manictime_readonly` создана и имеет правильные права
2. Проверьте файрвол - порт 5432 должен быть открыт
3. Проверьте настройки в `.env`
4. Попробуйте подключиться вручную: `psql -h HOST -U manictime_readonly -d ManicTimeReports`

### Проблема: Ошибка при миграциях

**Решение:**
```bash
# Проверьте подключение к служебной БД
psql -h localhost -U postgres -d dashboard_service

# Если БД не существует, создайте её
createdb dashboard_service

# Повторите миграции
alembic upgrade head
```

### Проблема: Frontend не может подключиться к Backend

**Решение:**
1. Проверьте, что Backend запущен на порту 8000
2. Проверьте настройки прокси в `vite.config.js`
3. Проверьте CORS настройки в `backend/app/main.py`
4. Проверьте консоль браузера на наличие ошибок

### Проблема: JWT токены не работают

**Решение:**
1. Убедитесь, что `JWT_SECRET_KEY` установлен в `.env`
2. Проверьте, что ключ достаточно длинный (минимум 32 символа)
3. Перезапустите Backend после изменения ключа

## Обновление системы

```bash
# 1. Остановите сервисы
docker-compose down  # или systemctl stop manictime-dashboard

# 2. Обновите код
git pull  # или скопируйте новые файлы

# 3. Обновите зависимости
cd backend
pip install -r requirements.txt

cd ../frontend
npm install

# 4. Примените миграции БД
cd backend
alembic upgrade head

# 5. Перезапустите сервисы
docker-compose up -d  # или systemctl restart manictime-dashboard
```

## Резервное копирование

### База данных служебной БД

```bash
# Создание резервной копии
pg_dump -h localhost -U postgres dashboard_service > backup_$(date +%Y%m%d).sql

# Восстановление
psql -h localhost -U postgres dashboard_service < backup_20240101.sql
```

### Файлы конфигурации

Всегда сохраняйте копию файла `.env` в безопасном месте!


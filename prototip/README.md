# Сервис Дашбордов и Аналитики для ManicTime

Корпоративный веб-сервис для визуализации и анализа данных ManicTime.

## Архитектура

- **Backend**: FastAPI (Python)
- **Frontend**: React (Vite)
- **Базы данных**: PostgreSQL (2 БД: ManicTime readonly + служебная БД)

## Структура проекта

```
dash/
├── backend/              # FastAPI приложение
│   ├── app/             # Основной код приложения
│   ├── alembic/         # Миграции базы данных
│   ├── scripts/         # Вспомогательные скрипты
│   └── requirements.txt
├── frontend/            # React приложение
│   ├── src/
│   └── package.json
└── README.md
```

## Установка и запуск

### Предварительные требования

1. PostgreSQL (для обеих баз данных)
2. Python 3.9+
3. Node.js 18+

### Шаг 1: Настройка базы данных ManicTime

**КРИТИЧЕСКИ ВАЖНО**: Создайте readonly роль для доступа к БД ManicTime:

```sql
-- 1. Создание роли
CREATE ROLE manictime_readonly LOGIN PASSWORD 'N0v1y_S3cur3_P@ssw0rd!';

-- 2. Права на подключение к БД
GRANT CONNECT ON DATABASE "ManicTimeReports" TO manictime_readonly;

-- 3. Права на схему
GRANT USAGE ON SCHEMA public TO manictime_readonly;

-- 4. Права на чтение таблиц
GRANT SELECT ON TABLE
    "Ar_Activity",
    "Ar_User",
    "Ar_Timeline",
    "Ar_CommonGroup",
    "Ar_Category",
    "Ar_CategoryGroup",
    "Ar_Environment"
TO manictime_readonly;
```

### Шаг 2: Настройка служебной базы данных

Создайте базу данных для сервиса:

```sql
CREATE DATABASE dashboard_service;
```

### Шаг 3: Настройка Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Создайте файл .env на основе .env.example
# Отредактируйте .env с вашими настройками

# Инициализация базы данных
alembic upgrade head

# Создание начальных ролей и администратора
python scripts/init_db.py

# Запуск сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 4: Настройка Frontend

```bash
cd frontend
npm install
npm run dev
```

Приложение будет доступно по адресу: http://localhost:3000

### Шаг 5: Первый вход

Используйте учетные данные, созданные скриптом `init_db.py`:
- **Логин**: `admin`
- **Пароль**: `admin123`

⚠️ **ВАЖНО**: Измените пароль администратора после первого входа через панель администратора!

## Конфигурация

### Переменные окружения (.env)

Все чувствительные данные (пароли, ключи) хранятся только в `.env` файле:

```env
# ManicTime Database (Read-Only)
MANICTIME_DB_HOST=localhost
MANICTIME_DB_PORT=5432
MANICTIME_DB_NAME=ManicTimeReports
MANICTIME_DB_USER=manictime_readonly
MANICTIME_DB_PASSWORD=ваш_пароль

# Service Database
SERVICE_DB_HOST=localhost
SERVICE_DB_PORT=5432
SERVICE_DB_NAME=dashboard_service
SERVICE_DB_USER=postgres
SERVICE_DB_PASSWORD=ваш_пароль

# JWT Settings
JWT_SECRET_KEY=сгенерируйте_случайный_ключ
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Настройка через UI (Панель администратора)

Нечувствительные параметры подключения к ManicTime (host, port, dbname) можно изменять через панель администратора. Пароль и пользователь всегда берутся только из `.env`.

## Функциональные модули

1. **Сводка** - Агрегированная гистограмма активности по категориям
2. **Хронология** - Индивидуальные линейки активности пользователей
3. **Метрика** - Числовые показатели эффективности в динамике
4. **Отпуска/Больничные** - Календарь отсутствий сотрудников
5. **Панель Администратора** - Управление пользователями и конфигурацией

## Безопасность

⚠️ **КРИТИЧЕСКИ ВАЖНО**:

1. Никогда не используйте учетные данные суперпользователя PostgreSQL в приложении
2. Создайте отдельную readonly роль для доступа к БД ManicTime
3. Храните пароли только в переменных окружения (.env)
4. Не коммитьте файл .env в систему контроля версий
5. Используйте надежные пароли для JWT_SECRET_KEY

## Разработка

### Структура API

API доступно по адресу: `http://localhost:8000/api/v1`

Документация: `http://localhost:8000/docs` (Swagger UI)

### Миграции базы данных

```bash
# Создание новой миграции
alembic revision --autogenerate -m "описание изменений"

# Применение миграций
alembic upgrade head

# Откат последней миграции
alembic downgrade -1
```

## Лицензия

Внутренний корпоративный проект.


FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Открытие порта
EXPOSE 8000

# Entrypoint: миграции + запуск API
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]


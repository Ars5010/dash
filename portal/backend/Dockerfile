FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY app /app/app
COPY tests /app/tests
COPY pytest.ini /app/pytest.ini
COPY requirements-dev.txt /app/requirements-dev.txt
COPY start.sh /app/start.sh
COPY scripts /app/scripts
RUN test -f /app/scripts/reset_user_password.py
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]


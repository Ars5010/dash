#!/bin/sh
set -e
set -u

echo "[entrypoint] running migrations"
alembic upgrade head

if [ "$#" -gt 0 ]; then
  echo "[entrypoint] running command: $*"
  exec "$@"
fi

echo "[entrypoint] starting api"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000


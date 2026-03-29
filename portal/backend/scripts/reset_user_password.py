#!/usr/bin/env python3
"""Сброс пароля пользователя по логину (без входа в веб).

Пример (Docker):
  docker compose exec backend python /app/scripts/reset_user_password.py admin admin123

Локально:
  cd backend && DATABASE_URL=postgresql+psycopg://... python scripts/reset_user_password.py admin admin123
"""
from __future__ import annotations

import os
import sys

# пакет app лежит в /app при запуске из образа
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    if len(sys.argv) != 3:
        print("Использование: python scripts/reset_user_password.py <логин> <новый_пароль>", file=sys.stderr)
        sys.exit(2)
    login = sys.argv[1].strip()
    new_pw = sys.argv[2]
    if not login or not new_pw:
        print("Логин и пароль не должны быть пустыми", file=sys.stderr)
        sys.exit(2)

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models import User

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.login == login).first()
        if not u:
            print(f"Пользователь с логином «{login}» не найден.", file=sys.stderr)
            sys.exit(1)
        u.hashed_password = hash_password(new_pw)
        db.commit()
        print(f"Пароль для «{login}» обновлён.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

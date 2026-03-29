"""
Скрипт для инициализации базы данных
Создает начальные роли и первого администратора
"""
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.core.database import ServiceSessionLocal, Base, service_engine
from app.models.service_db import AppRole, AppUser
from app.core.security import get_password_hash

def init_database():
    """Инициализация базы данных"""
    # Создание таблиц
    Base.metadata.create_all(bind=service_engine)
    
    db: Session = ServiceSessionLocal()
    
    try:
        # Создание ролей, если их нет
        admin_role = db.query(AppRole).filter(AppRole.role_name == "Admin").first()
        if not admin_role:
            admin_role = AppRole(role_name="Admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
            print("✓ Роль Admin создана")
        else:
            print("✓ Роль Admin уже существует")
        
        user_role = db.query(AppRole).filter(AppRole.role_name == "User").first()
        if not user_role:
            user_role = AppRole(role_name="User")
            db.add(user_role)
            db.commit()
            db.refresh(user_role)
            print("✓ Роль User создана")
        else:
            print("✓ Роль User уже существует")
        
        # Создание первого администратора, если его нет
        admin_user = db.query(AppUser).filter(AppUser.login == "admin").first()
        if not admin_user:
            admin_user = AppUser(
                login="admin",
                hashed_password=get_password_hash("admin123"),
                role_id=admin_role.id,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("✓ Создан администратор: login=admin, password=admin123")
            print("⚠ ВАЖНО: Измените пароль администратора после первого входа!")
        else:
            print("✓ Администратор уже существует")
        
        print("\n✓ Инициализация базы данных завершена успешно")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Ошибка при инициализации: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Инициализация базы данных...")
    init_database()


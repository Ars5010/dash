"""
Управление подключениями к базам данных
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Service Database (создаем первой, чтобы можно было читать конфигурацию)
service_engine = create_engine(
    f"postgresql://{settings.SERVICE_DB_USER}:{settings.SERVICE_DB_PASSWORD}@"
    f"{settings.SERVICE_DB_HOST}:{settings.SERVICE_DB_PORT}/{settings.SERVICE_DB_NAME}",
    pool_pre_ping=True,
    echo=False
)

ServiceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=service_engine)

Base = declarative_base()


def get_manictime_config():
    """Получение конфигурации подключения к ManicTime из служебной БД"""
    db = ServiceSessionLocal()
    try:
        from app.models.service_db import AppConfiguration
        config = {}
        config_items = db.query(AppConfiguration).filter(
            AppConfiguration.key.in_(["manictime_host", "manictime_port", "manictime_dbname"])
        ).all()
        
        for item in config_items:
            key = item.key.replace("manictime_", "")
            config[key] = item.value
        
        # Используем значения из БД, если они есть, иначе из .env
        host = config.get("host") or settings.MANICTIME_DB_HOST
        port = config.get("port") or settings.MANICTIME_DB_PORT
        dbname = config.get("dbname") or settings.MANICTIME_DB_NAME
        
        return {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": settings.MANICTIME_DB_USER,  # Всегда из .env
            "password": settings.MANICTIME_DB_PASSWORD  # Всегда из .env
        }
    except Exception as e:
        logger.warning(f"Не удалось загрузить конфигурацию из БД, используем .env: {e}")
        return {
            "host": settings.MANICTIME_DB_HOST,
            "port": settings.MANICTIME_DB_PORT,
            "dbname": settings.MANICTIME_DB_NAME,
            "user": settings.MANICTIME_DB_USER,
            "password": settings.MANICTIME_DB_PASSWORD
        }
    finally:
        db.close()


def get_manictime_engine():
    """Создание engine для ManicTime с учетом конфигурации из БД"""
    config = get_manictime_config()
    return create_engine(
        f"postgresql://{config['user']}:{config['password']}@"
        f"{config['host']}:{config['port']}/{config['dbname']}",
        pool_pre_ping=True,
        echo=False
    )


# ManicTime Database (Read-Only) - создается динамически
manictime_engine = None
ManicTimeSessionLocal = None


def get_manictime_db():
    """Dependency для получения сессии ManicTime БД (read-only)"""
    global manictime_engine, ManicTimeSessionLocal
    
    # Создаем engine динамически, чтобы учитывать изменения конфигурации
    if manictime_engine is None:
        manictime_engine = get_manictime_engine()
        ManicTimeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=manictime_engine)
    
    db = ManicTimeSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_service_db():
    """Dependency для получения сессии служебной БД"""
    db = ServiceSessionLocal()
    try:
        yield db
    finally:
        db.close()


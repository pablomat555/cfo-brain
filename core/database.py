import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger
from core.config import get_settings
from core.models import Base

settings = get_settings()
engine = create_engine(settings.cfo_db_url, connect_args={"check_same_thread": False} if "sqlite" in settings.cfo_db_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Создаёт таблицы если нет"""
    Base.metadata.create_all(bind=engine)
    
    # Дополнительно применяем миграцию 002 если таблицы observer не существуют
    apply_observer_migration()


def apply_observer_migration():
    """Применяет миграцию 002_observer_tables.sql если таблицы не существуют"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    observer_tables = {"monthly_metrics", "category_metrics", "anomaly_events"}
    tables_exist = all(table in existing_tables for table in observer_tables)
    
    if tables_exist:
        logger.debug("Observer tables already exist, skipping migration 002")
        return
    
    logger.info("Applying migration 002: creating observer tables")
    
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "002_observer_tables.sql")
    
    if not os.path.exists(migration_path):
        logger.error(f"Migration file not found: {migration_path}")
        # Таблицы будут созданы через Base.metadata.create_all выше
        return
    
    try:
        with open(migration_path, 'r') as f:
            sql_content = f.read()
        
        # Выполняем SQL миграцию
        with engine.connect() as conn:
            # SQLite требует выполнения каждого statement отдельно
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))
            conn.commit()
        
        logger.info("Migration 002 applied successfully")
        
    except Exception as e:
        logger.error(f"Error applying migration 002: {e}")
        # Не падаем, т.к. таблицы могут быть созданы через Base.metadata.create_all


def get_db():
    """Dependency для FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
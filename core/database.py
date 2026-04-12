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
    
    # Применяем миграцию 003 если таблицы капитального снапшота не существуют
    apply_capital_snapshot_migration()
    
    # Применяем миграцию 004 для фикса CHECK constraint liquidity_bucket
    apply_liquidity_constraint_fix_migration()


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


def apply_capital_snapshot_migration():
    """Применяет миграцию 003_capital_snapshot_tables.sql если таблицы не существуют"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    capital_tables = {"account_balances", "portfolio_positions"}
    tables_exist = all(table in existing_tables for table in capital_tables)
    
    if tables_exist:
        logger.debug("Capital snapshot tables already exist, skipping migration 003")
        return
    
    logger.info("Applying migration 003: creating capital snapshot tables")
    
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "003_capital_snapshot_tables.sql")
    
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
        
        logger.info("Migration 003 applied successfully")
        
    except Exception as e:
        logger.error(f"Error applying migration 003: {e}")
        # Не падаем, т.к. таблицы могут быть созданы через Base.metadata.create_all


def apply_liquidity_constraint_fix_migration():
    """Применяет миграцию 004_fix_liquidity_bucket_constraint.sql если таблица portfolio_positions существует"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "portfolio_positions" not in existing_tables:
        logger.debug("Table portfolio_positions does not exist, skipping migration 004")
        return
    
    # Проверяем, есть ли уже 'illiquid' в CHECK constraint
    # SQLite не позволяет напрямую проверить CHECK constraint, поэтому применяем миграцию всегда
    # если таблица существует (безопасно, так как миграция идемпотентна)
    logger.info("Applying migration 004: fixing liquidity_bucket CHECK constraint")
    
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "004_fix_liquidity_bucket_constraint.sql")
    
    if not os.path.exists(migration_path):
        logger.error(f"Migration file not found: {migration_path}")
        return
    
    try:
        with open(migration_path, 'r') as f:
            sql_content = f.read()
        
        # Выполняем SQL миграцию
        with engine.connect() as conn:
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))
            conn.commit()
        
        logger.info("Migration 004 applied successfully")
        
    except Exception as e:
        logger.error(f"Error applying migration 004: {e}")
        # Не падаем, т.к. constraint может быть уже исправлен


def get_db():
    """Dependency для FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import get_settings
from core.models import Base

settings = get_settings()
engine = create_engine(settings.db_url, connect_args={"check_same_thread": False} if "sqlite" in settings.db_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Создаёт таблицы если нет"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency для FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
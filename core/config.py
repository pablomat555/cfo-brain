from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_token: str
    db_url: str = "sqlite:///./cfo.db"
    openrouter_api_key: str | None = None
    owner_chat_id: int | None = None  # для еженедельного дайджеста

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
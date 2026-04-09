from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    telegram_token: str
    db_url: str = Field(default="sqlite:///./cfo.db", env="CFO_DB_URL")
    openrouter_api_key: str | None = None
    owner_chat_id: int | None = None  # для еженедельного дайджеста

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
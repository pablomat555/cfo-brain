from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    telegram_token: str
    cfo_db_url: str = "sqlite:////app/data/cfo.db"
    openrouter_api_key: str | None = None
    owner_chat_id: int | None = None  # для еженедельного дайджеста
    api_port: int = 8002  # порт для API (используется ботом)

    @validator("owner_chat_id", pre=True)
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
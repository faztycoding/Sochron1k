from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sochron:sochron_secret@localhost:5432/sochron1k"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI APIs
    GEMINI_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""

    # Price Data
    TWELVE_DATA_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # News pipeline — cap AI calls per run (respect free tier quota)
    # Gemini 2.5 Flash free tier = 20 requests/day
    # Setting to 15 leaves 5 for embeddings + safety buffer
    NEWS_MAX_ANALYSIS_PER_RUN: int = 15

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Central list — update here to add/remove pairs globally
TARGET_PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY", "GBP/USD", "AUD/USD"]
TARGET_CURRENCIES = ["EUR", "USD", "JPY", "GBP", "AUD"]

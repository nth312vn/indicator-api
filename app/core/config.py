from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # App basic info
    APP_NAME: str = "Technical Indicator API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Upstream Fiin Data API settings
    FIIN_DATA_API_BASE_URL: str = "http://127.0.0.1:8000"
    FIIN_DATA_API_PATH: str = "/api/v1/portfolio-construction/fiin_data/stockist"
    FIIN_API_TIMEOUT_SECONDS: float = 30.0
    FIIN_MAX_KEEPALIVE_CONNECTIONS: int = 20
    FIIN_MAX_CONNECTIONS: int = 100
    FIIN_FETCH_PAGE_SIZE: int = 1000

    # Auto fallback to mock data if live Fiin server is unreachable
    ENABLE_MOCK_FALLBACK: bool = True

    # Calculation concurrency
    MAX_WORKERS: Optional[int] = None  # None lets ThreadPoolExecutor choose based on CPU cores

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()

"""Application configuration loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./socmed.db"
    timezone: str = "Asia/Jakarta"

    # Threads (Meta)
    threads_access_token: str = ""
    threads_user_id: str = ""

    # X (Twitter)
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    x_bearer_token: str = ""

    # Scraper
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    scraper_timeout: int = 15

    # Basic Auth untuk web UI (kosongkan keduanya untuk matikan auth)
    auth_username: str = ""
    auth_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

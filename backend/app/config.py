from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI API Specification Generator"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    openai_api_key: str = ""
    openai_model: str = "gpt-5.4"
    openai_fast_model: str = "gpt-5.4-mini"
    openai_timeout_seconds: int = 60
    openai_context_char_limit: int = 4000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings from environment variables."""
    return Settings()

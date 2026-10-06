from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ASYNC_SCHEME = "postgresql+asyncpg"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: PostgresDsn
    transformer_delay_seconds: float = Field(0.1, ge=0)
    transformer_concurrency: int = Field(10, ge=1)
    max_list_length: int = Field(100, ge=1)
    max_string_length: int = Field(1000, ge=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("database_url")
    @classmethod
    def require_async_driver(cls, url: PostgresDsn) -> PostgresDsn:
        if url.scheme != ASYNC_SCHEME:
            raise ValueError(
                f"database_url must use the '{ASYNC_SCHEME}' scheme, got '{url.scheme}': "
                "the service talks to Postgres through SQLAlchemy's async engine"
            )

        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()

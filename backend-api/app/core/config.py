"""Application configuration.

Settings are loaded from environment variables (and a local .env file in
development). Never hardcode secrets here -- see .env.example for the list
of variables an operator must provide.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    PROJECT_NAME: str = "MercadoExpress API"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # Either set DATABASE_URL directly, or the POSTGRES_* parts below and it
    # will be assembled automatically.
    DATABASE_URL: PostgresDsn | None = None
    POSTGRES_USER: str = "mercadoexpress"
    POSTGRES_PASSWORD: str = "change-me"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mercadoexpress"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DATABASE_URL:
            return str(self.DATABASE_URL)
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str = Field(
        default="INSECURE-DEV-SECRET-CHANGE-ME-32BYTES-MIN",
        description="Secret key used to sign JWTs. MUST be overridden via env in every "
        "non-development environment.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --- Order pricing (placeholder business rules; adjust when real
    # tax/shipping logic or provider integrations are defined) ---
    TAX_RATE: float = 0.0
    FLAT_SHIPPING_FEE: float = 0.0


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (read once per process)."""
    return Settings()


settings = get_settings()

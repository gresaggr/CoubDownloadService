from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis & Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # File storage
    DOWNLOAD_FOLDER: str = "/app/downloads"
    MAX_FILE_SIZE_MB: int = 100

    # Security
    # ALLOWED_ORIGINS: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    SECRET_KEY: str = "change-me-in-production"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Monitoring
    SENTRY_DSN: str = ""
    ENABLE_METRICS: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()

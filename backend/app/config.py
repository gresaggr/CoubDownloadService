from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    DOWNLOAD_FOLDER: str = "/app/downloads"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

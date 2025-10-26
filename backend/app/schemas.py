import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FileStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class URLRequest(BaseModel):
    url: str = Field(..., description="URL для загрузки Coub-видео")

    @field_validator('url')
    @classmethod
    def validate_coub_url(cls, v: str) -> str:
        """Валидация URL - должен быть корректным Coub URL"""
        pattern = r'^https?://coub\.com/view/[\w-]+/?$'
        if not re.match(pattern, v.strip()):
            raise ValueError(
                'URL должен быть в формате: https://coub.com/view/VIDEO_ID'
            )
        return v.strip()


class FileRecordResponse(BaseModel):
    id: int
    url: str
    filename: Optional[str] = None
    status: FileStatus
    saved_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # Изменено с FileStatus на str для поддержки Celery статусов
    result: Optional[FileRecordResponse] = None
    progress: Optional[dict] = None  # Для отображения прогресса
    error: Optional[str] = None  # Для сообщений об ошибках


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

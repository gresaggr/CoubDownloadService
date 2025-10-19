from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class FileStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class URLRequest(BaseModel):
    url: str = Field(..., description="URL для загрузки Coub-видео")


class FileRecordResponse(BaseModel):
    id: int
    url: str
    filename: Optional[str]
    status: FileStatus
    saved_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    task_id: str
    status: FileStatus
    result: Optional[FileRecordResponse] = None

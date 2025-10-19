from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class URLRequest(BaseModel):
    url: str


class FileRecordResponse(BaseModel):
    id: int
    url: str
    filename: Optional[str]
    status: str
    saved_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[FileRecordResponse] = None

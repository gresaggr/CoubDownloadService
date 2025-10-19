from sqlalchemy import Column, Integer, String, DateTime, Enum
from datetime import datetime
from .database import Base

from enum import Enum as PyEnum


class FileStatus(str, PyEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=True)
    download_url = Column(String, nullable=True)
    saved_path = Column(String, nullable=True)
    status = Column(Enum(FileStatus), default=FileStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

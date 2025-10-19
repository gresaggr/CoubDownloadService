from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from .database import Base


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=True)
    download_url = Column(String, nullable=True)
    saved_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

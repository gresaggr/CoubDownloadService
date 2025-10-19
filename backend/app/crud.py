from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import FileRecord, FileStatus
from typing import Optional


async def get_file_by_url(db: AsyncSession, url: str) -> Optional[FileRecord]:
    result = await db.execute(select(FileRecord).filter(FileRecord.url == url))
    return result.scalars().first()


async def create_file_record(db: AsyncSession, url: str) -> FileRecord:
    db_file = FileRecord(url=url, status=FileStatus.pending)
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file


async def update_file_record(
        db: AsyncSession,
        file_id: int,
        filename: Optional[str] = None,
        download_url: Optional[str] = None,
        saved_path: Optional[str] = None,
        status: Optional[FileStatus] = None
) -> Optional[FileRecord]:
    result = await db.execute(select(FileRecord).filter(FileRecord.id == file_id))
    db_file = result.scalars().first()
    if not db_file:
        return None
    if filename is not None:
        db_file.filename = filename
    if download_url is not None:
        db_file.download_url = download_url
    if saved_path is not None:
        db_file.saved_path = saved_path
    if status is not None:
        db_file.status = status
    await db.commit()
    await db.refresh(db_file)
    return db_file


async def get_file_by_id(db: AsyncSession, file_id: int) -> Optional[FileRecord]:
    result = await db.execute(select(FileRecord).filter(FileRecord.id == file_id))
    return result.scalars().first()

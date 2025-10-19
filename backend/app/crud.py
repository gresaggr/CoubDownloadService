from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import FileRecord
from typing import Optional

async def get_file_by_url(db: AsyncSession, url: str) -> Optional[FileRecord]:
    result = await db.execute(select(FileRecord).filter(FileRecord.url == url))
    return result.scalars().first()

async def create_file_record(db: AsyncSession, url: str) -> FileRecord:
    db_file = FileRecord(url=url, status="pending")
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file

async def update_file_record(
    db: AsyncSession, 
    file_id: int, 
    filename: str = None,
    download_url: str = None,
    saved_path: str = None,
    status: str = None
):
    result = await db.execute(select(FileRecord).filter(FileRecord.id == file_id))
    db_file = result.scalars().first()
    if db_file:
        if filename:
            db_file.filename = filename
        if download_url:
            db_file.download_url = download_url
        if saved_path:
            db_file.saved_path = saved_path
        if status:
            db_file.status = status
        await db.commit()
        await db.refresh(db_file)
    return db_file

async def get_file_by_id(db: AsyncSession, file_id: int) -> Optional[FileRecord]:
    result = await db.execute(select(FileRecord).filter(FileRecord.id == file_id))
    return result.scalars().first()

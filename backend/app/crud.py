import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .models import FileRecord, FileStatus

logger = logging.getLogger(__name__)


async def get_file_by_url(db: AsyncSession, url: str) -> Optional[FileRecord]:
    """
    Получить запись файла по URL.

    Args:
        db: Асинхронная сессия базы данных
        url: URL файла для поиска

    Returns:
        FileRecord если найден, иначе None
    """
    try:
        result = await db.execute(
            select(FileRecord).filter(FileRecord.url == url)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error in get_file_by_url: {e}")
        raise


async def create_file_record(db: AsyncSession, url: str) -> FileRecord:
    """
    Создать новую запись файла.

    Args:
        db: Асинхронная сессия базы данных
        url: URL файла

    Returns:
        Созданная запись FileRecord
    """
    try:
        db_file = FileRecord(url=url, status=FileStatus.pending)
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        logger.info(f"Created file record: {db_file.id}")
        return db_file
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in create_file_record: {e}")
        raise


async def update_file_record(
        db: AsyncSession,
        file_id: int,
        filename: Optional[str] = None,
        download_url: Optional[str] = None,
        saved_path: Optional[str] = None,
        status: Optional[FileStatus] = None
) -> Optional[FileRecord]:
    """
    Обновить запись файла.

    Args:
        db: Асинхронная сессия базы данных
        file_id: ID записи для обновления
        filename: Новое имя файла (опционально)
        download_url: Новый URL загрузки (опционально)
        saved_path: Новый путь сохранения (опционально)
        status: Новый статус (опционально)

    Returns:
        Обновлённая запись FileRecord или None если не найдена
    """
    try:
        result = await db.execute(
            select(FileRecord).filter(FileRecord.id == file_id)
        )
        db_file = result.scalars().first()

        if not db_file:
            logger.warning(f"File record not found: {file_id}")
            return None

        # Обновляем только переданные поля
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
        logger.info(f"Updated file record: {file_id}")
        return db_file
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in update_file_record: {e}")
        raise


async def get_file_by_id(db: AsyncSession, file_id: int) -> Optional[FileRecord]:
    """
    Получить запись файла по ID.

    Args:
        db: Асинхронная сессия базы данных
        file_id: ID файла

    Returns:
        FileRecord если найден, иначе None
    """
    try:
        result = await db.execute(
            select(FileRecord).filter(FileRecord.id == file_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error in get_file_by_id: {e}")
        raise


async def get_files_by_status(
        db: AsyncSession,
        status: FileStatus,
        limit: int = 100
) -> List[FileRecord]:
    """
    Получить все файлы с определённым статусом.

    Args:
        db: Асинхронная сессия базы данных
        status: Статус файла для фильтрации
        limit: Максимальное количество записей

    Returns:
        Список FileRecord
    """
    try:
        result = await db.execute(
            select(FileRecord)
            .filter(FileRecord.status == status)
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error in get_files_by_status: {e}")
        raise


async def delete_file_record(db: AsyncSession, file_id: int) -> bool:
    """
    Удалить запись файла из базы данных.

    Args:
        db: Асинхронная сессия базы данных
        file_id: ID файла для удаления

    Returns:
        True если удалён, False если не найден
    """
    try:
        result = await db.execute(
            select(FileRecord).filter(FileRecord.id == file_id)
        )
        db_file = result.scalars().first()

        if not db_file:
            return False

        await db.delete(db_file)
        await db.commit()
        logger.info(f"Deleted file record: {file_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in delete_file_record: {e}")
        raise


async def get_pending_files(db: AsyncSession, limit: int = 10) -> List[FileRecord]:
    """
    Получить файлы в статусе pending (для обработки).

    Args:
        db: Асинхронная сессия базы данных
        limit: Максимальное количество записей

    Returns:
        Список FileRecord в статусе pending
    """
    return await get_files_by_status(db, FileStatus.pending, limit)

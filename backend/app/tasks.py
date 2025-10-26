import os
import httpx
import logging
import tempfile
import shutil
from celery import Task
from typing import Dict, Any

from backend.app.celery_app import celery_app
from backend.app.models import FileRecord, FileStatus
from backend.app.config import settings
from backend.app.utils import (
    generate_unique_filename,
    extract_coub_id,
    format_file_size
)
from backend.app.exceptions import (
    CoubAPIError,
    FileTooLargeError,
    DownloadError
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Логгер
logger = logging.getLogger("tasks")
logging.basicConfig(level=logging.INFO)

# Синхронная сессия для Celery
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace(
    "postgresql+asyncpg", "postgresql"
)
sync_engine = create_engine(sync_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=sync_engine)


@celery_app.task(
    bind=True,
    name="process_file_download",
    autoretry_for=(httpx.HTTPError, httpx.TimeoutException),
    retry_kwargs={'max_retries': 3, 'countdown': 10},
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=300,  # 5 минут максимум на задачу
    soft_time_limit=270  # Мягкий лимит для graceful shutdown
)
def process_file_download(self: Task, file_id: int, coub_url: str) -> Dict[str, Any]:
    """
    Асинхронная загрузка и обработка Coub видео.

    Args:
        file_id: ID записи в базе данных
        coub_url: URL Coub видео

    Returns:
        Dict с результатом выполнения
    """
    db = SessionLocal()

    try:
        # Получаем запись из БД
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not file_record:
            logger.error(f"File record not found: {file_id}")
            return {"error": "File record not found", "file_id": file_id}

        # Обновляем статус на processing
        file_record.status = FileStatus.processing
        db.commit()

        # Обновляем прогресс
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Получение информации о видео...'}
        )

        # Извлекаем ID из URL
        coub_id = extract_coub_id(coub_url)
        if not coub_id:
            raise CoubAPIError(f"Invalid Coub URL: {coub_url}")

        # Запрашиваем API Coub
        api_url = f"https://coub.com/api/v2/coubs/{coub_id}"
        logger.info(f"Fetching Coub API: {api_url}")

        try:
            response = httpx.get(api_url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CoubAPIError(f"Видео не найдено: {coub_id}")
            raise CoubAPIError(f"Ошибка API Coub: {e.response.status_code}")
        except httpx.TimeoutException:
            raise CoubAPIError("Timeout при обращении к API Coub")

        # Извлекаем данные
        try:
            title = data.get("title", f"coub_{coub_id}")
            download_url = data["file_versions"]["share"]["default"]
        except KeyError as e:
            logger.error(f"Missing key in API response: {e}")
            raise CoubAPIError(f"Некорректный ответ API: отсутствует {e}")

        if not download_url:
            raise CoubAPIError("URL для скачивания не найден в ответе API")

        # Генерируем уникальное имя файла
        original_filename = f"{title}.mp4"
        filename = generate_unique_filename(original_filename)

        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': f'Загрузка {filename}...'}
        )

        logger.info(f"Downloading: {filename} from {download_url}")

        # Загружаем файл с проверкой размера
        try:
            with httpx.stream('GET', download_url, timeout=60.0, follow_redirects=True) as stream_response:
                stream_response.raise_for_status()

                # Проверяем размер файла
                content_length = stream_response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
                    if file_size > settings.max_file_size_bytes:
                        raise FileTooLargeError(
                            f"Файл слишком большой: {format_file_size(file_size)} "
                            f"(максимум {settings.MAX_FILE_SIZE_MB} MB)"
                        )
                    logger.info(f"File size: {format_file_size(file_size)}")

                # Загружаем во временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    total_downloaded = 0
                    for chunk in stream_response.iter_bytes(chunk_size=8192):
                        tmp_file.write(chunk)
                        total_downloaded += len(chunk)

                        # Проверка размера во время загрузки
                        if total_downloaded > settings.max_file_size_bytes:
                            raise FileTooLargeError("Файл превышает максимальный размер")

                        # Обновляем прогресс
                        if content_length:
                            progress = 30 + int((total_downloaded / int(content_length)) * 60)
                            self.update_state(
                                state='PROGRESS',
                                meta={
                                    'current': progress,
                                    'total': 100,
                                    'status': f'Загружено {format_file_size(total_downloaded)}...'
                                }
                            )

                    tmp_path = tmp_file.name

        except httpx.HTTPStatusError as e:
            raise DownloadError(f"Ошибка загрузки: HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            raise DownloadError("Timeout при загрузке файла")

        self.update_state(
            state='PROGRESS',
            meta={'current': 95, 'total': 100, 'status': 'Сохранение файла...'}
        )

        # Создаём директорию если не существует
        os.makedirs(settings.DOWNLOAD_FOLDER, exist_ok=True)

        # Финальный путь к файлу
        final_path = os.path.join(settings.DOWNLOAD_FOLDER, filename)

        # Атомарное перемещение файла
        shutil.move(tmp_path, final_path)

        # Обновляем запись в БД
        file_record.filename = filename
        file_record.download_url = download_url
        file_record.saved_path = final_path
        file_record.status = FileStatus.completed
        db.commit()

        logger.info(f"Successfully downloaded: {final_path}")

        return {
            "status": "completed",
            "filename": filename,
            "file_id": file_id,
            "file_size": os.path.getsize(final_path)
        }

    except (CoubAPIError, FileTooLargeError, DownloadError) as e:
        logger.error(f"Expected error during download: {e}")
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if file_record:
            file_record.status = FileStatus.failed
            db.commit()
        return {"error": str(e), "file_id": file_id}

    except Exception as e:
        logger.exception(f"Unexpected error processing coub: {e}")
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if file_record:
            file_record.status = FileStatus.failed
            db.commit()
        # Пробрасываем исключение для retry
        raise

    finally:
        db.close()

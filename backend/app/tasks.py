import os
import httpx
import logging
from celery import Task
from backend.app.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import FileRecord, FileStatus
from backend.app.config import settings

# Логгер
logger = logging.getLogger("tasks")
logging.basicConfig(level=logging.INFO)

# Синхронная сессия для Celery
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
sync_engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=sync_engine)


@celery_app.task(bind=True, name="process_file_download", autoretry_for=(Exception,),
                 retry_kwargs={'max_retries': 3, 'countdown': 10})
def process_file_download(self: Task, file_id: int, coub_url: str):
    # bind = True -> self можно задействовать для retry и т.п.
    db = SessionLocal()
    try:
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not file_record:
            logger.error("File record not found")
            return {"error": "File record not found"}

        file_record.status = FileStatus.processing
        db.commit()

        coub_id = coub_url.strip("/").split("/")[-1]
        api_url = f"https://coub.com/api/v2/coubs/{coub_id}"
        response = httpx.get(api_url, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        try:
            title = data.get("title", f"coub_{file_id}")
            download_url = data["file_versions"]["share"]["default"]
        except Exception as extract_exc:
            logger.error(f"Error extracting url: {extract_exc}")
            file_record.status = FileStatus.failed
            db.commit()
            return {"error": "Error extracting url"}

        filename = f"{title}.mp4"
        if not title or not download_url:
            file_record.status = FileStatus.failed
            db.commit()
            logger.error("Missing filename or download_url in response")
            return {"error": "Missing filename or download_url in response"}

        logger.info(f"Download started: {filename} ({download_url})")
        download_response = httpx.get(download_url, timeout=60.0)
        download_response.raise_for_status()

        os.makedirs(settings.DOWNLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(settings.DOWNLOAD_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(download_response.content)

        file_record.filename = filename
        file_record.download_url = download_url
        file_record.saved_path = file_path
        file_record.status = FileStatus.completed
        db.commit()

        logger.info(f"Download completed: {file_path}")
        return {
            "status": "completed",
            "filename": filename,
            "file_id": file_id
        }

    except Exception as e:
        logger.error(f"Error processing coub: {e}")
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if file_record:
            file_record.status = FileStatus.failed
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()

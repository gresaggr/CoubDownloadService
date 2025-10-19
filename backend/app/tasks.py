import os
import httpx
from backend.app.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import FileRecord
from backend.app.config import settings

# Синхронная сессия для Celery
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
sync_engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=sync_engine)


@celery_app.task(bind=True, name="process_file_download")
def process_file_download(self, file_id: int, coub_url: str):
    db = SessionLocal()
    try:
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not file_record:
            return {"error": "File record not found"}

        file_record.status = "processing"
        db.commit()
        coub_id = coub_url.split('/')[-1]
        api_url = f'https://coub.com/api/v2/coubs/{coub_id}'
        response = httpx.get(api_url, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        try:
            title = data.get("title")
            download_url = data["file_versions"]["share"]["default"]
        except:
            return {"error": "Error extracting url"}

        filename = f'{title}.mp4'
        if not title or not download_url:
            file_record.status = "failed"
            db.commit()
            return {"error": "Missing filename or download_url in response"}

        print(filename, download_url)

        download_response = httpx.get(download_url, timeout=60.0)
        download_response.raise_for_status()

        os.makedirs(settings.DOWNLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(settings.DOWNLOAD_FOLDER, filename)

        with open(file_path, "wb") as f:
            f.write(download_response.content)

        file_record.filename = filename
        file_record.download_url = download_url
        file_record.saved_path = file_path
        file_record.status = "completed"
        db.commit()

        return {
            "status": "completed",
            "filename": filename,
            "file_id": file_id
        }

    except Exception as e:
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if file_record:
            file_record.status = "failed"
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()

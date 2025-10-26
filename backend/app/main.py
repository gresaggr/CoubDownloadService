import os
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from celery.result import AsyncResult

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.app.models import FileStatus
from backend.app import crud
from backend.app.celery_app import celery_app
from backend.app.database import get_session, init_db
from backend.app.schemas import (
    URLRequest,
    FileRecordResponse,
    TaskStatusResponse,
    ErrorResponse
)
from backend.app.config import settings
from backend.app.exceptions import (
    CoubAPIError,
    FileTooLargeError,
    FileNotFoundError as CustomFileNotFoundError
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle события приложения"""
    logger.info("Starting application...")

    app.state.limiter = limiter

    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Coub Download Service",
    description="Асинхронный сервис загрузки Coub видео",
    version="2.0.0",
    lifespan=lifespan
)

# Добавляем обработчик для rate limit
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: ограничить в .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов"""
    start_time = time.time()

    logger.info(f"Incoming request: {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Time: {process_time:.2f}s"
    )

    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(CoubAPIError)
async def coub_api_exception_handler(request: Request, exc: CoubAPIError):
    """Обработка ошибок Coub API"""
    logger.error(f"Coub API error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            detail=str(exc),
            error_code="COUB_API_ERROR"
        ).model_dump()
    )


@app.exception_handler(FileTooLargeError)
async def file_too_large_exception_handler(request: Request, exc: FileTooLargeError):
    """Обработка ошибки превышения размера файла"""
    logger.error(f"File too large: {exc}")
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content=ErrorResponse(
            detail=str(exc),
            error_code="FILE_TOO_LARGE"
        ).model_dump()
    )


@app.exception_handler(CustomFileNotFoundError)
async def file_not_found_exception_handler(request: Request, exc: CustomFileNotFoundError):
    """Обработка ошибки отсутствия файла"""
    logger.error(f"File not found: {exc}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            detail=str(exc),
            error_code="FILE_NOT_FOUND"
        ).model_dump()
    )


# Монтаж статики
app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")


@app.get("/", response_class=HTMLResponse, tags=["frontend"])
async def root():
    """Главная страница"""
    try:
        with open("/app/frontend/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Frontend not found")


@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "coub-download-service",
        "version": "2.0.0"
    }


@app.get("/health/db", tags=["monitoring"])
async def db_health_check(db: AsyncSession = Depends(get_session)):
    """Database health check"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        )


@app.get("/health/redis", tags=["monitoring"])
async def redis_health_check():
    """Redis health check"""
    try:
        # Проверяем Redis через Celery
        celery_app.control.inspect().ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable"
        )


@app.post(
    "/api/process",
    response_model=TaskStatusResponse,
    tags=["files"],
    summary="Начать обработку файла"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_url(
        request: Request,
        url_request: URLRequest,
        db: AsyncSession = Depends(get_session)
):
    """
    Обработка URL для загрузки Coub видео.

    - Проверяет, был ли файл ранее загружен
    - Если файл готов - возвращает информацию о нём
    - Если файл отсутствует - создаёт задачу на загрузку
    """
    url = url_request.url
    logger.info(f"Processing URL: {url}")

    try:
        # Проверяем существующую запись
        existing_file = await crud.get_file_by_url(db, url)

        if existing_file:
            logger.info(f"Found existing file record: {existing_file.id}")

            # Если файл завершён, проверяем его наличие на диске
            if existing_file.status == FileStatus.completed:
                if existing_file.saved_path and os.path.exists(existing_file.saved_path):
                    logger.info(f"File already exists: {existing_file.saved_path}")
                    return TaskStatusResponse(
                        task_id="",
                        status="completed",
                        result=FileRecordResponse.model_validate(existing_file)
                    )
                else:
                    # Файл был удалён, нужно перезагрузить
                    logger.warning(f"File missing on disk, re-downloading: {existing_file.id}")
                    await crud.update_file_record(
                        db,
                        file_id=existing_file.id,
                        saved_path=None,
                        status=FileStatus.pending
                    )
                    file_record = existing_file

            # Если файл в процессе обработки
            elif existing_file.status in [FileStatus.pending, FileStatus.processing]:
                logger.info(f"File already processing: {existing_file.id}")
                return TaskStatusResponse(
                    task_id="",
                    status=existing_file.status.value
                )

            # Если файл failed, пробуем снова
            else:
                logger.info(f"Retrying failed file: {existing_file.id}")
                await crud.update_file_record(
                    db,
                    file_id=existing_file.id,
                    status=FileStatus.pending
                )
                file_record = existing_file
        else:
            # Создаём новую запись
            logger.info("Creating new file record")
            file_record = await crud.create_file_record(db, url)

        # Отправляем задачу в Celery
        task = celery_app.send_task(
            "process_file_download",
            args=[file_record.id, url]
        )

        logger.info(f"Created Celery task: {task.id} for file: {file_record.id}")

        return TaskStatusResponse(
            task_id=task.id,
            status=FileStatus.pending.value
        )

    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Запись с таким URL уже существует"
        )

    except Exception as e:
        logger.exception(f"Unexpected error in process_url: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@app.get(
    "/api/task/{task_id}",
    response_model=TaskStatusResponse,
    tags=["files"],
    summary="Получить статус задачи"
)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_session)):
    """
    Проверка статуса задачи Celery.

    Возвращает:
    - pending/processing - задача в процессе
    - completed - задача завершена, файл готов
    - failed - задача завершилась с ошибкой
    """
    logger.info(f"Checking task status: {task_id}")

    try:
        task_result = AsyncResult(task_id, app=celery_app)

        # Если задача завершена
        if task_result.ready():
            result = task_result.result

            # Успешное завершение
            if isinstance(result, dict) and "file_id" in result and "error" not in result:
                file_record = await crud.get_file_by_id(db, result["file_id"])
                if file_record:
                    return TaskStatusResponse(
                        task_id=task_id,
                        status="completed",
                        result=FileRecordResponse.model_validate(file_record)
                    )

            # Завершилась с ошибкой
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"Task {task_id} failed: {result['error']}")
                return TaskStatusResponse(
                    task_id=task_id,
                    status="failed",
                    error=result['error']
                )

        # Задача в процессе - проверяем прогресс
        state = task_result.state
        info = task_result.info

        # Если есть информация о прогрессе
        if state == 'PROGRESS' and isinstance(info, dict):
            return TaskStatusResponse(
                task_id=task_id,
                status="processing",
                progress=info
            )

        # Обычные статусы Celery
        return TaskStatusResponse(
            task_id=task_id,
            status=state.lower()
        )

    except Exception as e:
        logger.exception(f"Error checking task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке статуса задачи"
        )


@app.get(
    "/api/download/{file_id}",
    response_class=FileResponse,
    tags=["files"],
    summary="Скачать файл"
)
async def download_file(file_id: int, db: AsyncSession = Depends(get_session)):
    """
    Скачивание обработанного файла по ID.

    Файл должен иметь статус 'completed' и существовать на диске.
    """
    logger.info(f"Download request for file_id: {file_id}")

    # Получаем запись из БД
    file_record = await crud.get_file_by_id(db, file_id)

    if not file_record:
        logger.warning(f"File record not found: {file_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден в базе данных"
        )

    if file_record.status != FileStatus.completed:
        logger.warning(f"File not ready: {file_id}, status: {file_record.status}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл ещё не готов. Статус: {file_record.status.value}"
        )

    if not file_record.saved_path or not os.path.exists(file_record.saved_path):
        logger.error(f"File missing on disk: {file_record.saved_path}")
        # Обновляем статус в БД
        await crud.update_file_record(
            db,
            file_id=file_id,
            status=FileStatus.failed
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл отсутствует на диске"
        )

    logger.info(f"Serving file: {file_record.saved_path}")

    return FileResponse(
        path=file_record.saved_path,
        filename=file_record.filename,
        media_type="application/octet-stream"
    )


@app.get("/api/files", response_model=list[FileRecordResponse], tags=["files"])
async def list_files(
        skip: int = 0,
        limit: int = 10,
        status_filter: Optional[FileStatus] = None,
        db: AsyncSession = Depends(get_session)
):
    """
    Получить список всех файлов с пагинацией.

    - skip: количество пропущенных записей
    - limit: максимальное количество записей (max 100)
    - status_filter: фильтр по статусу
    """
    from sqlalchemy.future import select

    limit = min(limit, 100)  # Максимум 100 записей

    query = select(crud.FileRecord).offset(skip).limit(limit)

    if status_filter:
        query = query.filter(crud.FileRecord.status == status_filter)

    result = await db.execute(query)
    files = result.scalars().all()

    return [FileRecordResponse.model_validate(f) for f in files]


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )

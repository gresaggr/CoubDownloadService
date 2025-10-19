import os
import logging

from contextlib import asynccontextmanager

import uvicorn

from celery.result import AsyncResult

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .celery_app import celery_app
from .database import get_session, init_db
from .schemas import URLRequest, FileRecordResponse, TaskStatusResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(
    title="Coub Download Service",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: ограничить в .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтаж статики (frontend)
app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("/app/frontend/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.post("/api/process", response_model=TaskStatusResponse)
async def process_url(request: URLRequest, db: AsyncSession = Depends(get_session)):
    existing_file = await crud.get_file_by_url(db, request.url)
    if existing_file and existing_file.status == "completed":
        logger.info(f"File already processed: {request.url}")
        return TaskStatusResponse(
            task_id="",
            status="completed",
            result=FileRecordResponse.model_validate(existing_file)
        )

    file_record = await crud.create_file_record(db, request.url)
    logger.info(f"Created new file record: {file_record.id}")

    task = celery_app.send_task(
        "process_file_download",
        args=[file_record.id, request.url]
    )
    logger.info(f"Celery Task started: id={task.id}")

    return TaskStatusResponse(
        task_id=task.id,
        status="pending"
    )


@app.get("/api/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_session)):
    task_result = AsyncResult(task_id, app=celery_app)
    logger.info(f"Checking task status: {task_id}")
    if task_result.ready():
        result = task_result.result
        if isinstance(result, dict) and "file_id" in result:
            file_record = await crud.get_file_by_id(db, result["file_id"])
            return TaskStatusResponse(
                task_id=task_id,
                status="completed",
                result=FileRecordResponse.model_validate(file_record)
            )
    return TaskStatusResponse(
        task_id=task_id,
        status=task_result.state.lower()
    )


@app.get("/api/download/{file_id}", response_class=FileResponse)
async def download_file(file_id: int, db: AsyncSession = Depends(get_session)):
    file_record = await crud.get_file_by_id(db, file_id)
    if not file_record or file_record.status != "completed":
        logger.warning(f"Attempt to download unavailable file id={file_id}")
        raise HTTPException(status_code=404, detail="File not found or not ready")

    if not os.path.exists(file_record.saved_path):
        logger.error(f"Local file not found: {file_record.saved_path}")
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=file_record.saved_path,
        filename=file_record.filename,
        media_type="application/octet-stream"
    )


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

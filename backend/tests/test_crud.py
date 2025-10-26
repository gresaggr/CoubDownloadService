import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import crud
from backend.app.models import FileStatus


class TestFileRecordCRUD:
    """Тесты CRUD операций с FileRecord"""
    
    @pytest.mark.asyncio
    async def test_create_file_record(self, db_session: AsyncSession, sample_coub_url: str):
        """Тест создания записи файла"""
        record = await crud.create_file_record(db_session, sample_coub_url)
        
        assert record.id is not None
        assert record.url == sample_coub_url
        assert record.status == FileStatus.pending
        assert record.filename is None
        assert record.saved_path is None
    
    @pytest.mark.asyncio
    async def test_get_file_by_url_existing(self, db_session: AsyncSession, sample_coub_url: str):
        """Тест получения существующей записи по URL"""
        created = await crud.create_file_record(db_session, sample_coub_url)
        
        found = await crud.get_file_by_url(db_session, sample_coub_url)
        
        assert found is not None
        assert found.id == created.id
        assert found.url == sample_coub_url
    
    @pytest.mark.asyncio
    async def test_get_file_by_url_nonexistent(self, db_session: AsyncSession):
        """Тест получения несуществующей записи"""
        found = await crud.get_file_by_url(db_session, "https://coub.com/view/nonexistent")
        
        assert found is None
    
    @pytest.mark.asyncio
    async def test_get_file_by_id_existing(self, db_session: AsyncSession, sample_coub_url: str):
        """Тест получения записи по ID"""
        created = await crud.create_file_record(db_session, sample_coub_url)
        
        found = await crud.get_file_by_id(db_session, created.id)
        
        assert found is not None
        assert found.id == created.id
    
    @pytest.mark.asyncio
    async def test_get_file_by_id_nonexistent(self, db_session: AsyncSession):
        """Тест получения несуществующей записи по ID"""
        found = await crud.get_file_by_id(db_session, 99999)
        
        assert found is None
    
    @pytest.mark.asyncio
    async def test_update_file_record_status(self, db_session: AsyncSession, sample_coub_url: str):
        """Тест обновления статуса файла"""
        created = await crud.create_file_record(db_session, sample_coub_url)
        
        updated = await crud.update_file_record(
            db_session,
            file_id=created.id,
            status=FileStatus.processing
        )
        
        assert updated is not None
        assert updated.status == FileStatus.processing
    
    @pytest.mark.asyncio
    async def test_update_file_record_all_fields(self, db_session: AsyncSession, sample_coub_url: str):
        """Тест обновления всех полей файла"""
        created = await crud.create_file_record(db_session, sample_coub_url)
        
        updated = await crud.update_file_record(
            db_session,
            file_id=created.id,
            filename="test_video.mp4",
            download_url="https://example.com/video.mp4",
            saved_path="/app/downloads/test_video.mp4",
            status=FileStatus.completed
        )
        
        assert updated is not None
        assert updated.filename == "test_video.mp4"
        assert updated.download_url == "https://example.com/video.mp4"
        assert updated.saved_path == "/app/downloads/test_video.mp4"
        assert updated.status == FileStatus.completed
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_file(self, db_session: AsyncSession):
        """Тест обновления несуществующей записи"""
        updated = await crud.update_file_record(
            db_session,
            file_id=99999,
            status=FileStatus.completed
        )
        
        assert updated is None
    
    @pytest.mark.asyncio
    async def test_get_files_by_status(self, db_session: AsyncSession):
        """Тест получения файлов по статусу"""
        # Создаём несколько записей
        await crud.create_file_record(db_session, "https://coub.com/view/test1")
        await crud.create_file_record(db_session, "https://coub.com/view/test2")
        
        record3 = await crud.create_file_record(db_session, "https://coub.com/view/test3")
        await crud.update_file_record(db_session, record3.id, status=FileStatus.completed)
        
        # Получаем только pending
        pending_files = await crud.get_files_by_status(db_session, FileStatus.pending)
        assert len(pending_files) >= 2
        
        # Получаем только completed
        completed_files = await crud.get_files_by_status(db_session, FileStatus.completed)
        assert len(completed_files) >= 1
    
    @pytest.mark.asyncio
    async def test_delete_file_record(self, db_session: AsyncSession, sample_coub_url: str):
        """Тест удаления записи"""
        created = await crud.create_file_record(db_session, sample_coub_url)
        
        deleted = await crud.delete_file_record(db_session, created.id)
        assert deleted is True
        
        # Проверяем что запись действительно удалена
        found = await crud.get_file_by_id(db_session, created.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, db_session: AsyncSession):
        """Тест удаления несуществующей записи"""
        deleted = await crud.delete_file_record(db_session, 99999)
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_get_pending_files(self, db_session: AsyncSession):
        """Тест получения pending файлов"""
        # Создаём несколько pending файлов
        await crud.create_file_record(db_session, "https://coub.com/view/pending1")
        await crud.create_file_record(db_session, "https://coub.com/view/pending2")
        
        pending = await crud.get_pending_files(db_session, limit=10)
        
        assert len(pending) >= 2
        for file in pending:
            assert file.status == FileStatus.pending

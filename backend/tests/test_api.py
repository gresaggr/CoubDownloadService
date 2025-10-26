import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import FileStatus


class TestHealthEndpoints:
    """Тесты health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
    
    @pytest.mark.asyncio
    async def test_db_health_check(self, client: AsyncClient):
        response = await client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"


class TestProcessURL:
    """Тесты endpoint обработки URL"""
    
    @pytest.mark.asyncio
    async def test_process_valid_url(self, client: AsyncClient, sample_coub_url: str):
        """Тест успешной обработки валидного URL"""
        response = await client.post(
            "/api/process",
            json={"url": sample_coub_url}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["pending", "processing"]
    
    @pytest.mark.asyncio
    async def test_process_invalid_url_format(self, client: AsyncClient):
        """Тест обработки невалидного формата URL"""
        response = await client.post(
            "/api/process",
            json={"url": "not-a-valid-url"}
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_process_non_coub_url(self, client: AsyncClient, invalid_coub_url: str):
        """Тест обработки не-Coub URL"""
        response = await client.post(
            "/api/process",
            json={"url": invalid_coub_url}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_process_duplicate_url(self, client: AsyncClient, sample_coub_url: str):
        """Тест повторной обработки того же URL"""
        # Первый запрос
        response1 = await client.post(
            "/api/process",
            json={"url": sample_coub_url}
        )
        assert response1.status_code == 200
        
        # Второй запрос того же URL
        response2 = await client.post(
            "/api/process",
            json={"url": sample_coub_url}
        )
        assert response2.status_code == 200
        # Не должна создаваться новая задача
    
    @pytest.mark.asyncio
    async def test_process_empty_url(self, client: AsyncClient):
        """Тест с пустым URL"""
        response = await client.post(
            "/api/process",
            json={"url": ""}
        )
        assert response.status_code == 422


class TestTaskStatus:
    """Тесты проверки статуса задачи"""
    
    @pytest.mark.asyncio
    async def test_get_task_status_invalid_id(self, client: AsyncClient):
        """Тест проверки несуществующей задачи"""
        response = await client.get("/api/task/invalid-task-id-12345")
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data


class TestDownload:
    """Тесты скачивания файлов"""
    
    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, client: AsyncClient):
        """Тест скачивания несуществующего файла"""
        response = await client.get("/api/download/99999")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_download_without_file_id(self, client: AsyncClient):
        """Тест скачивания без ID"""
        response = await client.get("/api/download/")
        assert response.status_code == 404


class TestListFiles:
    """Тесты получения списка файлов"""
    
    @pytest.mark.asyncio
    async def test_list_files_empty(self, client: AsyncClient):
        """Тест получения пустого списка файлов"""
        response = await client.get("/api/files")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_files_with_pagination(self, client: AsyncClient):
        """Тест пагинации"""
        response = await client.get("/api/files?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    @pytest.mark.asyncio
    async def test_list_files_with_status_filter(self, client: AsyncClient):
        """Тест фильтрации по статусу"""
        response = await client.get("/api/files?status_filter=pending")
        assert response.status_code == 200


class TestRateLimiting:
    """Тесты rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_not_exceeded(self, client: AsyncClient, sample_coub_url: str):
        """Тест что нормальное количество запросов проходит"""
        for _ in range(3):
            response = await client.post(
                "/api/process",
                json={"url": f"{sample_coub_url}"}
            )
            # Должны проходить без ошибок
            assert response.status_code in [200, 409]  # 409 если дубликат


class TestFrontend:
    """Тесты фронтенда"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Тест главной страницы"""
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

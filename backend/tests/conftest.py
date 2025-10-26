import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from httpx import AsyncClient, ASGITransport
from backend.app.database import Base, get_session
from backend.app.main import app

# Тестовая база данных (через docker-compose сервис "db")
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/test_filedb"


@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Единый event loop для всех async фикстур"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator:
    """Создает тестовый движок PostgreSQL"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Изолированная AsyncSession для каждого теста"""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        # безопасный rollback в рамках того же event loop
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP клиент для тестирования API (работает в том же event loop)"""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db_session):
    """Очищает все таблицы между тестами"""
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()


@pytest.fixture
def sample_coub_url() -> str:
    return "https://coub.com/view/test123"


@pytest.fixture
def invalid_coub_url() -> str:
    return "https://example.com/invalid"

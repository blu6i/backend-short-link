from collections.abc import AsyncGenerator, Callable
from typing import Any, cast

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from main import app
from src.core.database import async_db
from src.core.rd import RedisDatabase
from src.core.settings import settings
from src.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def fake_async_redis():
    """Фейковая асинхронная Redis для тестов."""
    async_redis = RedisDatabase(
        host=settings.redis.redis_host,
        port=settings.redis.redis_port,
        db=settings.redis.redis_db,
        password=settings.redis.redis_password,
        prefix="test",
    )
    yield async_redis

    client = await async_redis.get_client()
    await client.flushall()
    await async_redis.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Создает схемы таблиц перед запуском тестов и удаляет после."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Изолированная сессия БД на каждый тест с откатом транзакции."""
    async with test_engine.connect() as connection:
        # Начинаем внешнюю транзакцию
        transaction = await connection.begin()

        # Привязываем сессию к открытому соединению
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        yield session
        await transaction.rollback()
        await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """
    HTTP-клиент для вызова эндпоинтов FastAPI с переопределенной сессией БД.

    Args:
        db_session (AsyncSession): Асинхронная сессия

    Returns:
        AsyncGenerator[AsyncClient, None]: асинхронный генератор

    """

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    # Подменяем зависимость БД в FastAPI
    app.dependency_overrides[async_db.get_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

"""Подключение к базе данных и управление асинхронными сессиями."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.settings import settings


class DataBase:
    """Предоставляет асинхронный движок и фабрику сессий SQLAlchemy."""

    def __init__(
        self,
        url: str,
        echo: bool = False,
        echo_pool: bool = False,
        max_overflow: int = 5,
        pool_size: int = 5,
    ):
        """
        Инициализирует движок и фабрику асинхронных сессий.

        Args:
            url: Строка подключения к базе данных.
            echo: Включает вывод SQL-запросов в лог.
            echo_pool: Включает вывод событий пула соединений.
            max_overflow: Максимальное число дополнительных соединений.
            pool_size: Размер пула соединений.

        """
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            echo_pool=echo_pool,
            max_overflow=max_overflow,
            pool_size=pool_size,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False
        )

    async def dispose(self) -> None:
        """Освобождает ресурсы движка и закрывает соединения."""
        await self.engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Предоставляет сессию базы данных как зависимость FastAPI."""
        async with self.session_factory() as session:
            yield session

    @asynccontextmanager
    async def get_context_session(self):
        """Предоставляет сессию базы данных в контекстном менеджере."""
        async with self.session_factory() as session:
            yield session

    async def healthcheck(self) -> bool:
        """Проверяет доступность базы данных простым SQL-запросом."""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Database healthcheck failed: {}", e)
            return False


async_db = DataBase(
    url=settings.db.get_db,
    echo=settings.db.echo,
    echo_pool=settings.db.echo_pool,
    max_overflow=settings.db.max_overflow,
    pool_size=settings.db.pool_size,
)

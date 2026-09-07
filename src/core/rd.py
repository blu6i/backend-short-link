"""Redis настройки."""

from contextlib import asynccontextmanager

import redis.asyncio as redis

from src.core.settings import settings


class RedisDatabase:
    """Управляет пулом соединений и операциями с Redis."""

    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        password: str | None = None,
        prefix: str = "",
        max_connections: int = 5000,
    ):
        """
        Инициализирует параметры подключения к Redis.

        Args:
            host (str): IP хостинга,
            port (str): порт,
            db (int): номер БД,
            password (str): пароль. default=None
            prefix (str): Префикс, добавляемый ко всем ключам.
            flag_nx (bool): Флаг для Set if Not eXists. default=False
            max_connections (int): максимальное кол-во подключений
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self._pool = None
        self._client = None
        self.prefix = prefix
        self.max_connections = max_connections

    async def init_pool(self):
        """Initialize the connection pool."""
        if self._pool is None:
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                max_connections=self.max_connections,
                decode_responses=True,
            )

    async def get_client(self):
        """Get an asynchronous Redis client."""
        if self._client is None:
            await self.init_pool()
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    @asynccontextmanager
    async def connection(self):
        """Provide an asynchronous context manager for a connection."""
        client = await self.get_client()
        try:
            yield client
        finally:
            pass

    async def close(self):
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None
            self._client = None

    # ===== Convenience methods with a prefix =====
    def _full_key(self, key: str) -> str:
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key

    async def set(self, key: str, value, ex: int = 300, nx: bool = False) -> bool:
        """
        Асинхронно сохраняет значение ключа с ограниченным сроком жизни.

        Args:
            key: Ключ для сохранения.
            value: Значение ключа.
            ex: Срок жизни ключа в секундах.

        """
        async with self.connection() as r:
            result = await r.set(self._full_key(key), value, ex=ex, nx=nx)
            return bool(result)

    async def get(self, key: str):
        """
        Асинхронно получает значение по ключу.

        Args:
            key (key): Ключ для поиска.

        """
        async with self.connection() as r:
            return await r.get(self._full_key(key))

    async def delete(self, key):
        """
        Асинхронно удаляет ключ.

        Args:
            key: Ключ для удаления.

        """
        async with self.connection() as r:
            await r.delete(self._full_key(key))

    async def exists(self, key) -> bool:
        """
        Проверяет наличие ключа в Redis.

        Args:
            key: Ключ для проверки.

        Returns:
            Признак существования ключа.

        """
        async with self.connection() as r:
            return await r.exists(self._full_key(key)) > 0

    async def keys(self, pattern="*"):
        """
        Асинхронно возвращает ключи, соответствующие шаблону.

        Args:
            pattern: Шаблон поиска, например `task:*`.

        """
        async with self.connection() as r:
            return await r.keys(self._full_key(pattern))


async_redis = RedisDatabase(
    host=settings.redis.redis_host,
    port=settings.redis.redis_port,
    db=settings.redis.redis_db,
    password=settings.redis.redis_password,
    max_connections=settings.redis.max_connections,
)


async def get_async_redis() -> RedisDatabase:
    """Зависимость для инъекции базового Redis (кэш, блокировки)."""
    return async_redis

"""Настройки для проекта."""

from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTToken(BaseModel):
    """Настройки для генерации JWT токена."""

    token: str
    algorithm: str

    @property
    def get_algorithm(self):
        """Получение алгоритма."""
        return self.algorithm

    @property
    def get_token(self):
        """Получение токена."""
        return self.token


class AuthSettings(BaseModel):
    """Настройки cookies авторизации."""

    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None


class LogSettings(BaseModel):
    """Настройки для логера."""

    log_level: str
    log_rotation: str
    log_retention: str
    # -----------------------------
    # Формат логов
    # -----------------------------
    # time - время события
    # level - уровень логирования
    # file - файл, где произошёл лог
    # line - строка
    # message - сообщение
    log_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level}</level> | "
        "<cyan>{file}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )


class HashedSaltSettings(BaseModel):
    """Соль для хэширования."""

    hashed_ip_salt: str


class RedisSettings(BaseModel):
    """Настройки для Redis."""

    redis_host: str
    redis_port: int
    redis_db: int = 0
    redis_db_broker: int = 1
    redis_db_backend: int = 2
    redis_password: str | None = None
    max_connections: int = 3000

    @property
    def get_redis_url(self):
        """Ссылка для подключения к Redis."""
        password = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def get_url_broker(self):
        """Ссылка для подключения к Redis брокера."""
        password = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db_broker}"


class DBSettings(BaseModel):
    """Настройки для подключения к БД."""

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    postgres_host: str
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 50
    max_overflow: int = 10

    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    @property
    def get_async_db(self):
        """Ссылка для асинхронного подключения к БД."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def get_sync_db(self):
        """Ссылка для синхронного подключения к БД."""
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class Cors(BaseModel):
    """Настройка CORS."""

    allowed_origins: list[str] = ["*"]  # Разрешенные домены
    allow_credentials: bool = False  # Разрешение передачи учетных данных в запросы
    allow_methods: list[str] = [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ]  # Разрешенные методы
    allow_headers: list[str] = ["*"]  # Разрешенные заголовки


class Url(BaseModel):
    """Ссылка сайта."""

    url: str = "localhost:8000"

    @property
    def get_url(self) -> str:
        """Возвращает ссылку сайта."""
        return self.url


class ApiTokens(BaseModel):
    """Токены к внешним АПИ."""

    ip_checked: str


class Settings(BaseSettings):
    """Все настройки."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        json_file=None,
    )
    db: DBSettings
    log: LogSettings
    redis: RedisSettings
    jwt: JWTToken
    auth: AuthSettings = AuthSettings()
    cors: Cors
    url: Url
    salt: HashedSaltSettings
    api_token: ApiTokens


settings = Settings()  # type: ignore[call-arg]

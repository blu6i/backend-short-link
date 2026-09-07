"""Модуль аунтификации и авторизации."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_db
from src.core.exceptions import AlreadyExistsException, NotFoundException
from src.core.rd import RedisDatabase, get_async_redis
from src.core.settings import settings
from src.repositories.user import user_repo
from src.schemas.user import UserReadSchem

async_session = Annotated[AsyncSession, Depends(async_db.get_session)]
async_session_rd = Annotated[RedisDatabase, Depends(get_async_redis)]
REFRESH_BLACKLIST_PREFIX = "auth:blacklist:refresh:"


def hash_password(password: str) -> str:
    """
    Хеширует пароль через bcrypt.

    Args:
        password (str): строка для хэширования

    Returns:
        str: хэш строки

    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    """
    Проверяет, подходит ли введенный пароль к хэшу из нашей базы.

    Args:
        password (str): пароль пользователя
        hashed_password (str): пароль пользователя из бд

    Returns:
        bool: результат проверки

    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def decode_token(token: str) -> dict:
    """
    Декодирует JWT токен.

    Args:
        token (str): JWT токен

    Raises:
        HTTPException: Ошибка при невалидном токене

    Returns:
        dict: Данные payload

    """
    try:
        payload = jwt.decode(
            token, settings.jwt.get_token, algorithms=[settings.jwt.get_algorithm]
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def check_token(
    session: async_session,
    accessToken: str = Cookie(None),
) -> UserReadSchem:
    """
    Проверка JWT токена из куки. Если токена нет или он кривой — кидает 401 ошибку.

    Args:
        session (async_session): сессия БД
        accessToken (str, optional): access token. Defaults to Cookie(None).

    Raises:
        HTTPException: невалидный токен

    Returns:
        UserBase: модель пользователя

    """
    if not accessToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(accessToken)

    type_token = payload.get("type")
    if type_token != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    try:
        user = await user_repo.get(user_id, session)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user  # type: ignore


async def check_refresh_token(
    session: async_session,
    session_rd: async_session_rd,
    refreshToken: str = Cookie(None),
) -> UserReadSchem:
    """
    Проверка JWT токена из куки. Если токена нет или он кривой — кидает 401 ошибку.

    Args:
        session (async_session): сессия БД
        refreshToken (str, optional): access token. Defaults to Cookie(None).
        session_rd (async_session_rd): Redis для проверки blacklist.

    Raises:
        HTTPException: невалидный токен

    Returns:
        UserBase: модель пользователя

    """
    if not refreshToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(refreshToken)

    if await session_rd.exists(refresh_token_blacklist_key(refreshToken)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    type_token = payload.get("type")
    if type_token != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    try:
        user = await user_repo.get(user_id, session)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user  # type: ignore


def refresh_token_blacklist_key(token: str) -> str:
    """Возвращает непрямой Redis-ключ для refresh-токена."""
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    return f"{REFRESH_BLACKLIST_PREFIX}{token_hash}"


async def revoke_refresh_token(token: str, redis: RedisDatabase) -> None:
    """Добавляет refresh-токен в Redis blacklist до окончания его срока."""
    payload = decode_token(token)
    expires_at = int(payload["exp"])
    ttl = max(1, expires_at - int(datetime.now(UTC).timestamp()))
    await redis.set(refresh_token_blacklist_key(token), "1", ex=ttl, nx=True)


async def check_access_user(
    session: async_session,
    accessToken: str | None = Cookie(None),
) -> UserReadSchem | None:
    """
    Проверка прав доступа для создания ссылки.

    Если пользователь не авторизован,
    то возвращает None и в ручке ссылка будет
    создаваться без привязки к пользователю.

    Args:
        session (async_session): сессия БД
        accessToken (str | None, optional): access токен из куки.
            Defaults to Cookie(None).

    Returns:
        UserReadSchem | None: _description_

    """
    if not accessToken:
        return None
    return await check_token(session, accessToken)


def generate_token(user_id: int, life_time: int, type_token: str) -> str:
    """
    Генерирует новый JWT токен для пользователя.

    Args:
        user_id (int): ИД пользователя
        life_time (int): время жизни токена (в секундах)
        type_token (str): тип токена

    Returns:
        str: jwt токен

    """
    expire = datetime.now(UTC) + timedelta(seconds=life_time)
    return jwt.encode(
        payload={
            "sub": str(user_id),
            "exp": expire,
            "type": type_token,
            "jti": uuid4().hex,
        },
        key=settings.jwt.get_token,
        algorithm=settings.jwt.get_algorithm,
    )


async def registration_locks(email: str, username: str, redis: RedisDatabase) -> bool:
    """
    Кэширование email и username для блокировки уникальностей.

    Args:
        email (str): почта пользователя
        username (str): никнейм пользователя
        redis (RedisDatabase): сессия редис

    Returns:
        bool: результат блокировки

    """
    # Пытаемся заблокировать email
    if not await redis.set(f"lock:email:{email}", "1", ex=5, nx=True):
        raise AlreadyExistsException(message="Введенная почта пользователя занята")
    # Пытаемся заблокировать username
    if not await redis.set(f"lock:user:{username}", "1", ex=5, nx=True):
        # Откатываем блокировку email
        await redis.delete(f"lock:email:{email}")
        raise AlreadyExistsException(message="Введенное имя пользователя занято")

    return True

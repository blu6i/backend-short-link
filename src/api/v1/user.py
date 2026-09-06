"""API для пользователя."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_db
from src.core.exceptions import AlreadyExistsException, NotFoundException
from src.core.rd import RedisDatabase, get_async_redis
from src.core.settings import settings
from src.repositories.user import user_repo
from src.schemas.user import UserCreateSchem, UserLoginShem, UserReadSchem
from src.services.auth import (
    check_password,
    check_refresh_token,
    check_token,
    generate_token,
    hash_password,
    registration_locks,
)

router = APIRouter(prefix="/users", tags=["users"])

async_session_db = Annotated[AsyncSession, Depends(async_db.get_session)]
user_read_access = Annotated[UserReadSchem, Depends(check_token)]
user_read_refresh = Annotated[UserReadSchem, Depends(check_refresh_token)]
async_session_rd = Annotated[RedisDatabase, Depends(get_async_redis)]


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserReadSchem
)
async def register_user(
    user_data: UserCreateSchem,
    session_db: async_session_db,
    session_rd: async_session_rd,
    response: Response,
):
    """
    Регистрация пользователя и генерация JWT токенов (access, refresh).

    Args:
        user_data (UserCreateSchem): Схема пользователя с данными для регистрации
        session_db (async_session_db): Сессия БД
        session_rd (async_session_rd): Сессия Редис
        response (Response): Кука

    """
    try:
        await registration_locks(user_data.email, user_data.username, session_rd)
    except AlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    db_password = hash_password(user_data.password)
    try:
        user = await user_repo.create(session_db, user_data, db_password)
    except AlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    refresh_token = generate_token(user.id, 60 * 60 * 24 * 7, "refresh")
    access_token = generate_token(user.id, 60 * 5, "access")
    response.set_cookie(
        key="accessToken",
        value=access_token,
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
        max_age=60 * 5,
    )
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
        max_age=60 * 60 * 24 * 7,
    )
    return user


@router.post("/login", status_code=status.HTTP_200_OK, response_model=UserReadSchem)
async def login_user(
    user_data: UserLoginShem, session: async_session_db, response: Response
):
    """
    Аунтификация пользователя и генерация JWT токенов (access, refresh).

    Args:
        user_data (UserLoginShem): данные для аунтификации.
        session (async_session): сессия БД
        response (Response): Кука

    """
    try:
        user = await user_repo.get_by_email(session, user_data.email)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверно указана почта или пароль",
        )
    if not check_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверно указана почта или пароль",
        )
    refresh_token = generate_token(user.id, 60 * 60 * 24 * 7, "refresh")
    access_token = generate_token(user.id, 60 * 5, "access")
    response.set_cookie(
        key="accessToken",
        value=access_token,
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
        max_age=60 * 5,
    )
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
        max_age=60 * 60 * 24 * 7,
    )
    return user


@router.get("/me", response_model=UserReadSchem)
async def get_current_user(user_data: user_read_access):
    """Возвращает пользователя из действующего access-токена."""
    return user_data


@router.post("/refresh_token", status_code=status.HTTP_200_OK)
async def refresh_token(user_data: user_read_refresh, response: Response):
    """
    Выход пользователя.

    Args:
        user_data (user_read): данные авторизованного пользователя
        response (Response): Кука

    """
    # TODO: Добавить внесение старых токенов в ЧС
    refresh_token = generate_token(user_data.id, 60 * 60 * 24 * 7, "refresh")
    access_token = generate_token(user_data.id, 60 * 5, "access")
    response.set_cookie(
        key="accessToken",
        value=access_token,
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
        max_age=60 * 5,
    )
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
        max_age=60 * 60 * 24 * 7,
    )


@router.post("/unlogin", status_code=status.HTTP_204_NO_CONTENT)
async def unlogin_user(user_data: user_read_access, response: Response):
    """
    Выход пользователя.

    Args:
        user_data (user_read): данные авторизованного пользователя
        response (Response): Кука

    """
    # TODO: Добавить внесение токена в ЧС
    response.delete_cookie(
        key="accessToken",
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
    )
    response.delete_cookie(
        key="refreshToken",
        httponly=True,
        samesite=settings.auth.cookie_samesite,
        secure=settings.auth.cookie_secure,
        domain=settings.auth.cookie_domain,
    )

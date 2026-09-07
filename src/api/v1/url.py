"""Шаблон CRUD-роутера для ресурсов версии API v1."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_db
from src.core.exceptions import AlreadyExistsException
from src.core.rd import RedisDatabase, get_async_redis
from src.repositories.url import url_repo
from src.schemas.general import PaginationParams
from src.schemas.statistics import StatisticsScale, UrlStatisticsSchema
from src.schemas.url import PaginationUrlSchema, UrlCreateSchem, UrlReadSchema
from src.schemas.user import UserReadSchem
from src.services.auth import check_access_user, check_token
from src.services.statistics import statistics_service
from src.utils.hashed import hashed_url

router = APIRouter(prefix="/urls", tags=["url"])

async_session_db = Annotated[AsyncSession, Depends(async_db.get_session)]
async_session_rd = Annotated[RedisDatabase, Depends(get_async_redis)]
pagination_query = Annotated[PaginationParams, Query()]
user_auth = Annotated[UserReadSchem, Depends(check_access_user)]
user_read_access = Annotated[UserReadSchem, Depends(check_token)]

COUNT_TRY_SAVE = 5


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UrlReadSchema)
async def create_url(
    session: async_session_db,
    session_rd: async_session_rd,
    original_url: UrlCreateSchem,
    user: user_auth,
):
    """Создание ссылки."""
    url = str(original_url.original_url)
    if user:
        if await url_repo.exists_by_full_url_user(
            session, user.id, str(original_url.original_url)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ссылка уже была сокращена",
            )
        try_save = 0
        while try_save < COUNT_TRY_SAVE:
            salt = f"salt_{try_save}"
            short_url = hashed_url(url, salt, str(user.id))
            try:
                result = await session_rd.set(
                    key=short_url, value=url, ex=60 * 60 * 24, nx=True
                )
                if not result:
                    raise AlreadyExistsException()
                try:
                    url_base = await url_repo.create_url(session, url, short_url, user.id)
                except SQLAlchemyError:
                    logger.exception("Ошибка БД при сохранении короткой ссылки")
                    raise
                return url_base
            except AlreadyExistsException as e:  # noqa: F841
                try_save += 1
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Сервер исчерпал попытки создания уникальной ссылки",
        )
    short_url = hashed_url(url)
    result = await session_rd.set(key=short_url, value=url, ex=60 * 60 * 24, nx=True)
    if result:
        return UrlReadSchema(original_url=url, short_url=short_url)
    original_url_rd = await session_rd.get(key=short_url)
    if original_url_rd == str(original_url.original_url):
        return UrlReadSchema(original_url=url, short_url=short_url)
    try_save = 0
    while try_save < COUNT_TRY_SAVE:
        salt = f"salt_{try_save}"
        short_url = hashed_url(url, salt)
        try:
            result = await session_rd.set(
                key=short_url, value=url, ex=60 * 60 * 24, nx=True
            )
            if not result:
                raise AlreadyExistsException()
            return UrlReadSchema(original_url=url, short_url=short_url)
        except AlreadyExistsException as e:  # noqa: F841
            try_save += 1
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Сервер исчерпал попытки создания уникальной ссылки",
    )


@router.get("/", response_model=PaginationUrlSchema)
async def get_all_url(session: async_session_db, pagination: pagination_query):
    """Получение всех ссылок с пагинацией."""
    result = await url_repo.get_paginated_url(
        session, pagination.page, pagination.per_page
    )
    return result


@router.get("/my", response_model=PaginationUrlSchema)
async def get_user_url(
    session: async_session_db, pagination: pagination_query, user_data: user_auth
):
    """Получение всех ссылок с пагинацией."""
    result = await url_repo.get_paginated_user_url(
        session, user_data.id, pagination.page, pagination.per_page
    )
    return result


@router.get("/{short_url}", response_model=UrlStatisticsSchema)
async def get_url(
    session: async_session_db,
    user_data: user_read_access,
    short_url: Annotated[
        str,
        Path(
            pattern=r"^[0-9a-zA-Z]{6}$",
            description="Base62 строка длиной ровно 6 символов",
            examples=["aB9xYz", "00a1Z9"],
        ),
    ],
    scale: Annotated[StatisticsScale, Query(...)],
):
    """Получение агрегированной статистики переходов по ссылке."""
    return await statistics_service.get_url_statistics(
        session, short_url, user_data.id, scale
    )


@router.delete("/{short_url}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_url(
    session_db: async_session_db,
    session_rd: async_session_rd,
    user_data: user_auth,
    short_url: str,
):
    """Удаление пользовательской ссылки."""
    await url_repo.delete(session_db, short_url, user_data.id)
    await session_rd.delete(short_url)

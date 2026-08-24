"""Шаблон CRUD-роутера для ресурсов версии API v1."""

from random import randint
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_db
from src.core.exceptions import AlreadyExistsException, NotFoundException
from src.core.rd import url_redis
from src.repositories.url import url_repo
from src.schemas.general import PaginationParams
from src.schemas.url import PaginationUrlSchema, UrlCreateSchem, UrlReadSchema
from src.utils.hashed_url import hashed_url

router = APIRouter(prefix="/urls", tags=["url"])

async_session = Annotated[AsyncSession, Depends(async_db.get_session)]

COUNT_TRY_SAVE = 5


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UrlReadSchema)
async def create_url(session: async_session, original_url: UrlCreateSchem):
    """Создание ссылки."""
    try_save = 0
    url = str(original_url.original_url)
    while try_save < COUNT_TRY_SAVE:
        salt = f"salt_{randint(0, 999)}"
        short_url = hashed_url(url, salt)
        try:
            result = await url_redis.set(key=short_url, value=url, ex=60 * 60 * 24)
            if not result:
                raise AlreadyExistsException()
            # TODO: сделать проверку на авторизацию пользователя
            url_base = await url_repo.create_url(session, url, short_url)
            return url_base
        except AlreadyExistsException as e:  # noqa: F841
            try_save += 1
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Сервер исчерпал попытки создания уникальной ссылки",
    )


@router.get("/{short_url}", response_model=UrlReadSchema)
async def get_url(
    session: async_session,
    short_url: Annotated[
        str,
        Path(
            pattern=r"^[0-9a-zA-Z]{6}$",
            description="Base62 строка длиной ровно 6 символов",
            examples=["aB9xYz", "00a1Z9"],
        ),
    ],
):
    """Получение информации и статистики об оригинальной ссылки."""
    "TODO: Добавить вывод статистики"
    try:
        url_data = await url_repo.get_url(session, short_url)
        return url_data
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/", response_model=PaginationUrlSchema)
async def get_all_url(
    session: async_session, pagination: Annotated[PaginationParams, Query()]
):
    """Получение всех ссылок с пагинацией."""
    result = await url_repo.get_paginated_url(
        session, pagination.page, pagination.per_page
    )
    return result

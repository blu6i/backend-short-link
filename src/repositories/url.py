"""Репозиторий для модели ссылок."""

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AlreadyExistsException, NotFoundException
from src.core.logger import log
from src.models.url import UrlBase


class UrlRepository:
    """Репозитория для модели ссылок."""

    def __init__(self, model: type[UrlBase]) -> None:
        """Инициализация репозитория."""
        self.model = model

    async def create_url(self, session: AsyncSession, original_url: str, short_url: str):
        """Создание записи в таблице links."""
        new_link = self.model(original_url=original_url, short_url=short_url)
        session.add(new_link)
        try:
            await session.commit()
            return new_link
        except IntegrityError as e:  # noqa: F841
            await session.rollback()
            raise AlreadyExistsException(message=f"Короткая ссылка занята ({short_url})")

    async def get_full_url(self, session: AsyncSession, short_url: str):
        """Получение полной ссылки по сжатой."""
        stmt = select(self.model.original_url).where(self.model.short_url == short_url)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    async def get_paginated_url(
        self, session: AsyncSession, page: int = 1, per_page: int = 10
    ):
        """Получение всех длинных ссылок с пагинацией."""
        offset_value = (page - 1) * per_page

        stmt = select(func.count()).select_from(self.model)
        total_items = await session.scalar(stmt) or 0

        if total_items == 0:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
            }

        stmt = (
            select(self.model)
            .order_by(self.model.id)
            .offset(offset_value)
            .limit(per_page)
        )
        result = await session.scalars(stmt)
        items = result.all()

        return {
            "items": items,
            "total": total_items,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_items + per_page - 1) // per_page,
        }

    async def exists_by_short_url(self, session: AsyncSession, short_url: str) -> bool:
        """Проверка на существовании ссылки в БД."""
        stmt = select(exists().where(self.model.short_url == short_url))
        result = await session.scalar(stmt)
        return bool(result)

    async def get_url(self, session: AsyncSession, short_url: str) -> UrlBase:
        """Получение данных о ссылке."""
        stmt = select(UrlBase).where(UrlBase.short_url == short_url)
        result = await session.scalar(stmt)
        log.debug(result)
        if not result:
            raise NotFoundException("Ссылка не найдена")
        return result


url_repo = UrlRepository(UrlBase)

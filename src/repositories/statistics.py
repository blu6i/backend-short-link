from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundException
from src.models.statistic_url import StatisticUrlBase
from src.models.url import UrlBase
from src.schemas.statistics import StatisticsScale


class StatisticsRepository:
    """Доступ к событиям переходов и ссылке-владельцу."""

    async def get_clicks(
        self,
        session: AsyncSession,
        short_url: str,
        user_id: int,
    ) -> list[datetime]:
        """Возвращает времена переходов по ссылке владельца."""
        url_stmt = select(UrlBase).where(
            UrlBase.short_url == short_url,
            UrlBase.user_id == user_id,
            UrlBase.is_active,
        )
        url = await session.scalar(url_stmt)
        if not url:
            raise NotFoundException("Ссылка не найдена")

        clicks_stmt = (
            select(StatisticUrlBase.clicked_at)
            .where(StatisticUrlBase.url_id == url.id)
            .order_by(StatisticUrlBase.clicked_at)
        )
        return list((await session.scalars(clicks_stmt)).all())

    @staticmethod
    def aggregate(
        clicks: list[datetime], scale: StatisticsScale
    ) -> list[tuple[date, int]]:
        """Группирует события по выбранному календарному масштабу."""
        grouped: defaultdict[date, int] = defaultdict(int)
        for clicked_at in clicks:
            if scale is StatisticsScale.DAY:
                period = clicked_at.date()
            elif scale is StatisticsScale.MONTH:
                period = clicked_at.date().replace(day=1)
            else:
                period = clicked_at.date().replace(month=1, day=1)
            grouped[period] += 1
        return sorted(grouped.items())


statistics_repo = StatisticsRepository()

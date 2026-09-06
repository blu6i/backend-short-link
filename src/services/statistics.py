from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.statistics import statistics_repo
from src.schemas.statistics import (
    StatisticPointSchema,
    StatisticsScale,
    UrlStatisticsSchema,
)


class StatisticsService:
    """Сервис формирования статистики переходов."""

    async def get_url_statistics(
        self,
        session: AsyncSession,
        short_url: str,
        user_id: int,
        scale: StatisticsScale,
    ) -> UrlStatisticsSchema:
        """Возвращает агрегированную статистику ссылки."""
        clicks = await statistics_repo.get_clicks(session, short_url, user_id)
        aggregated = statistics_repo.aggregate(clicks, scale)
        return UrlStatisticsSchema(
            short_url=short_url,
            scale=scale,
            total=len(clicks),
            items=[
                StatisticPointSchema(period=period, count=count)
                for period, count in aggregated
            ],
        )


statistics_service = StatisticsService()

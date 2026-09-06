from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class StatisticsScale(StrEnum):
    """Допустимый масштаб агрегации статистики."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class StatisticPointSchema(BaseModel):
    """Количество переходов за один период."""

    period: date
    count: int = Field(ge=0)


class UrlStatisticsSchema(BaseModel):
    """Статистика переходов по короткой ссылке."""

    short_url: str
    scale: StatisticsScale
    total: int = Field(ge=0)
    items: list[StatisticPointSchema]

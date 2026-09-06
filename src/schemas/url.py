"""Схема для ссылок."""

from pydantic import BaseModel, HttpUrl, computed_field

from src.core.settings import settings


class UrlBaseSchem(BaseModel):
    """Базовая схема для ссылок."""

    original_url: str


class UrlCreateSchem(BaseModel):
    """Схема для создания ссылок."""

    original_url: HttpUrl


class UrlReadSchema(UrlBaseSchem):
    """Схема для чтения ссылок."""

    short_url: str
    model_config = {"from_attributes": True}


class UrlRedirectSchema(BaseModel):
    """Схема для редирект линка."""

    short_url: str

    @computed_field
    @property
    def full_url(self) -> str:
        """Возвращает полную ссылку на сайт."""
        return f"{settings.url.get_url}/{self.short_url}"


class PaginationUrlSchema(BaseModel):
    """Схема всех URL с пагинацией."""

    items: list[UrlReadSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
    model_config = {"from_attributes": True}

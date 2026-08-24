"""Общие схемы."""

from typing import Annotated

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Схема пагинации."""

    page: Annotated[int, Field(1, ge=1, description="Номер страницы")]
    per_page: Annotated[int, Field(10, ge=1, le=100, description="Количество элементов")]

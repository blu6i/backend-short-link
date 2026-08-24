"""Модель ссылок."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixins import ActiveMixin, CreatedAtMixin, PKInt


class UrlBase(PKInt, CreatedAtMixin, ActiveMixin, Base):
    """Модель ссылок для базы данных."""

    __tablename__ = "urls"

    original_url: Mapped[str] = mapped_column(String(4096), nullable=False)
    short_url: Mapped[str] = mapped_column(String(6), nullable=False)

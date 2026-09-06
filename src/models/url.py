"""Модель ссылок."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.mixins import ActiveMixin, CreatedAtMixin, PKInt

if TYPE_CHECKING:
    from src.models.user import UserBase


class UrlBase(PKInt, CreatedAtMixin, ActiveMixin, Base):
    """Модель ссылок для базы данных."""

    __tablename__ = "urls"
    __table_args__ = (UniqueConstraint("user_id", "original_url"),)

    original_url: Mapped[str] = mapped_column(String(4096), nullable=False)
    short_url: Mapped[str] = mapped_column(String(6), nullable=False)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    user: Mapped[UserBase] = relationship(back_populates="links")

"""Модель пользователя."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.mixins import ActiveMixin, CreatedAtMixin, PKInt

if TYPE_CHECKING:
    from src.models.url import UrlBase


class UserBase(PKInt, CreatedAtMixin, ActiveMixin, Base):
    """Модель пользователя."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    links: Mapped[list[UrlBase]] = relationship(
        uselist=True, cascade="all, delete-orphan", back_populates="user"
    )

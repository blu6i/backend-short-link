"""Миксины, добавляющие моделям признаки активности."""

from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column


class ActiveMixin:
    """Добавляет моделям SQLAlchemy признак активности записи."""

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

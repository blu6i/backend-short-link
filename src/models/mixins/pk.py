"""Миксины для определения первичных ключей моделей."""

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class PKInt:
    """Добавляет моделям целочисленный первичный ключ `id`."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

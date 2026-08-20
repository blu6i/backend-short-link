"""Базовый класс SQLAlchemy-моделей и их соглашения о метаданных."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from src.core.settings import settings


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей приложения."""

    metadata = MetaData(naming_convention=settings.db.naming_convention)

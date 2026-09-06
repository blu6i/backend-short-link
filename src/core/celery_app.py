"""Celery настройки."""

from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.settings import settings

# 1. Инициализация Celery
celery_app = Celery(
    "worker",
    broker=settings.redis.get_url_broker,
    include=["src.tasks.statistics"],
)

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# 2. Поднятие синхронной сессии для задач
sync_engine = create_engine(settings.db.get_sync_db)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

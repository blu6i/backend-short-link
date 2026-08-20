"""Корневой пакет API приложения."""

from fastapi import APIRouter

router = APIRouter(prefix="/api")

# Подключение роутера
"""
router.include_router(
    сам_роутер
    prefix="/Версия/апи",
    tags=["Теги"]
)
"""

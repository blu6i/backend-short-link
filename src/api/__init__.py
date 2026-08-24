"""Корневой пакет API приложения."""

from fastapi import APIRouter

router = APIRouter(prefix="/api")

# Подключение роутера выполняется в `main.py`, чтобы FastAPI корректно
# развернул маршруты вложенного роутера.

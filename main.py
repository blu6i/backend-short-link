"""
Главное приложение FastAPI с безопасностью.

Для запуска:
    python -m uvicorn app.backend.apps:app --reload --host 0.0.0.0 --port 8000

Для Docker:
    docker build -t api-secure .
    docker run -p 8000:8000 api-secure
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import api
from src.core.database import async_db
from src.core.exceptions import AppException
from src.core.logger import logger
from src.core.rd import async_redis
from src.core.settings import settings


# Инициализация БД и Redis при запуске приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("🚀 Secure API запущено")

    # Инициализация БД
    health = await async_db.healthcheck()
    if not health:
        logger.error("❌ Ошибка подключения к БД!")
    else:
        logger.info("✅ БД подключена успешно")

    # Инициализация Redis
    await async_redis.init_pool()
    try:
        async with async_redis.connection() as r:
            await r.ping()
        logger.info("✅ Redis подключен успешно")
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Ошибка подключения к Redis: {e}")

    yield

    # Shutdown
    logger.info("🛑 Secure API остановлено")
    await async_db.dispose()
    await async_redis.close()


# Создание приложения FastAPI
app = FastAPI(
    title="ShortUrl API",
    description="API для сохранения и выдачи кода",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    lifespan=lifespan,
)


# CORS Middleware - поддержка веб-клиентов и других приложений
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=bool(settings.cors.allow_credentials),
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)


# Глобальный обработчик кастомных исключений
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Обработчик исключений AppException.

    Возвращает стандартизированный JSON-ответ с соответствующим HTTP-статусом.
    """
    logger.warning(f"Ошибка приложения: {exc.message} (Status Code: {exc.status_code})")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# Подключение маршрутов
app.include_router(api.router)


# Хелс-чек
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Проверка здоровья приложения.

    Может использоваться сервисом мониторинга или load balancer'ом.
    """
    db_health = await async_db.healthcheck()
    return {
        "status": "healthy" if db_health else "degraded",
        "message": "API работает" if db_health else "БД недоступна",
        "database": "connected" if db_health else "disconnected",
    }


# Корневая схема
@app.get("/", tags=["Info"])
async def root():
    """
    Информация об API.

    - Документация: `/docs` (Swagger UI)
    - ReDoc: `/redoc`
    - Health Check: `/health`
    """
    return {
        "name": "ShortUrl API",
        "version": "1.0.0",
        "description": "API для сокращений ссылок и статистики переходов",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

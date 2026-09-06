"""
Главное приложение FastAPI с безопасностью.

Для запуска:
    python -m uvicorn app.backend.apps:app --reload --host 0.0.0.0 --port 8000

Для Docker:
    docker build -t api-secure .
    docker run -p 8000:8000 api-secure
"""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.url import router as url_router
from src.api.v1.user import router as user_router
from src.core.database import async_db
from src.core.exceptions import AppException
from src.core.logger import logger
from src.core.rd import async_redis
from src.core.settings import settings
from src.repositories.url import url_repo


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
    try:
        await async_redis.init_pool()
        async with async_redis.connection() as redis_client:
            await redis_client.ping()
        logger.info("✅ базовый Redis подключен успешно")
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Обработчик исключений Exception.

    Возвращает стандартизированный JSON-ответ с соответствующим HTTP-статусом.
    """
    logger.exception(f"Критическая ошибка: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера. Мы уже работаем над этим."},
    )


# Подключение маршрутов
app.include_router(url_router, prefix="/api")
app.include_router(user_router, prefix="/api")


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
# @app.get("/", tags=["Info"])
# async def root():
#     """
#     Информация об API.

#     - Документация: `/docs` (Swagger UI)
#     - ReDoc: `/redoc`
#     - Health Check: `/health`
#     """
#     return {
#         "name": "ShortUrl API",
#         "version": "1.0.0",
#         "description": "API для сокращений ссылок и статистики переходов",
#         "docs": "/docs",
#         "health": "/health",
#     }


@app.get("/{short_url}")
async def redirect(
    session: Annotated[AsyncSession, Depends(async_db.get_session)], short_url: str
):
    """Редирект на оригининальную ссылку."""
    # original_url = await url_repo.get_full_url(session, short_url)
    original_url = await async_redis.get(short_url)
    if not original_url:
        original_url = await url_repo.get_full_url(session, short_url)
        if not original_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оригинальная ссылка не найдена",
            )
        await async_redis.set(key=short_url, value=original_url, ex=60 * 60 * 24, nx=True)
    return RedirectResponse(
        str(original_url), status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

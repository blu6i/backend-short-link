# ShortcutLink

Сервис сокращения ссылок с гостевым режимом, личным кабинетом, Redis-кэшем и фоновой статистикой переходов.

## Возможности

- создание коротких ссылок без регистрации;
- регистрация и JWT-аутентификация через HttpOnly cookies;
- создание и просмотр ссылок пользователя;
- редирект `307 Temporary Redirect`;
- сбор IP, User-Agent, страны и города в фоне через Celery;
- Nginx reverse proxy с передачей IP в `X-Real-IP`;
- PostgreSQL, Redis и Alembic-миграции.

## Требования

- Docker Desktop с Docker Compose;
- для локального запуска без Docker: Python 3.14+ и `uv`;
- доступный порт `8000` для Nginx.

## Запуск через Docker

1. Создайте файл окружения:

```bash
cp .env.example .env
```

2. Измените в `.env` обязательные значения:

```env
DB__POSTGRES_PASSWORD=strong_database_password
REDIS__REDIS_PASSWORD=strong_redis_password
JWT__TOKEN=<случайный_секрет_минимум_32_байта>
SALT__HASHED_IP_SALT=<случайная_соль>
API_TOKEN__IP_CHECKED=<токен_2ip>
```

JWT-секрет можно создать командой:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Для production с HTTPS включите защищённые cookies:

```env
AUTH__COOKIE_SECURE=true
AUTH__COOKIE_SAMESITE=lax
AUTH__COOKIE_DOMAIN=example.com
CORS__ALLOWED_ORIGINS=["https://example.com"]
CORS__ALLOW_CREDENTIALS=true
```

3. Соберите и запустите сервисы:

```bash
docker compose up --build -d
```

Приложение доступно через Nginx:

```text
http://localhost:8000
```

FastAPI не публикует порт наружу напрямую. Публичным входом является только Nginx.

Проверка состояния:

```bash
docker compose ps
curl http://localhost:8000/health
```

Логи:

```bash
docker compose logs -f app

docker compose logs -f worker
```

Остановка:

```bash
docker compose down
```

Для удаления данных PostgreSQL и Redis используйте `docker compose down -v`.

## Локальный запуск

Запустите PostgreSQL и Redis, создайте `.env`, затем установите зависимости:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload --port 8000
```

Celery worker запускается отдельным процессом:

```bash
uv run celery -A src.core.celery_app:celery_app worker --loglevel=INFO
```

## Тесты и проверки

```bash
uv run python -m pytest
uv run ruff check .
```

Тесты используют отдельную SQLite-базу для FastAPI и Redis из тестового окружения. Внешний geo API и отправка Celery-задач в тестах заменяются mock-объектами.

## Документация

- [API](docs/API.md)
- [ERD](docs/ERD.md)
- [Roadmap](docs/roadmap.md)
- [Пример переменных окружения](.env.example)

## Стек

Python 3.14, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, Nginx, Pydantic Settings, Pytest, HTTPX и `uv`.

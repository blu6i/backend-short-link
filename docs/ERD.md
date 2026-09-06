# Схема базы данных

```mermaid
erDiagram
    USERS {
        int id PK
        varchar username UK "NOT NULL, max 32"
        varchar email UK "NOT NULL, max 255"
        varchar hashed_password "NOT NULL, max 255"
        datetime created_at "NOT NULL"
        boolean is_active "NOT NULL"
    }

    URLS {
        int id PK
        int user_id FK "NULL для гостевых ссылок"
        varchar original_url "NOT NULL, max 4096"
        varchar short_url "NOT NULL, max 6"
        datetime created_at "NOT NULL"
        boolean is_active "NOT NULL"
    }

    STATISTIC_URLS {
        int id PK
        int url_id FK
        datetime clicked_at "NOT NULL"
        varchar hashed_ip "NOT NULL, max 255"
        varchar user_agent "NOT NULL, max 255"
        varchar country "NULL, max 255"
        varchar city "NULL, max 255"
    }

    USERS ||--o{ URLS : creates
    URLS ||--o{ STATISTIC_URLS : receives
```

## `users`

- `id` — первичный ключ.
- `username` — уникальное имя пользователя, максимум 32 символа.
- `email` — уникальный email, максимум 255 символов.
- `hashed_password` — bcrypt-хэш пароля, максимум 255 символов.
- `created_at` — дата регистрации.
- `is_active` — флаг активности пользователя.

## `urls`

- `id` — первичный ключ.
- `user_id` — внешний ключ на `users.id`, может быть `NULL` для гостевых ссылок.
- `original_url` — исходный URL, максимум 4096 символов.
- `short_url` — короткий Base62-ключ длиной 6 символов.
- `created_at` — дата создания.
- `is_active` — флаг мягкого удаления.
- `(user_id, original_url)` — уникальное ограничение для ссылок пользователя.

Гостевые ссылки не записываются в PostgreSQL и живут в Redis 24 часа. Пользовательские ссылки сохраняются в PostgreSQL и кэшируются в Redis.

## `statistic_urls`

- `id` — первичный ключ.
- `url_id` — внешний ключ на `urls.id`, удаляется каскадно.
- `clicked_at` — время перехода.
- `hashed_ip` — SHA-256 хэш IP с солью, исходный IP не сохраняется.
- `user_agent` — User-Agent клиента.
- `country`, `city` — данные geo API, могут быть `NULL`.

Статистика создаётся Celery worker после redirect. Запрос к внешнему geo API ограничен Celery rate limit `3/s` на worker.

## Redis

Redis не является частью ERD. Он используется для:

- хранения гостевых коротких ссылок;
- кэширования пользовательских ссылок;
- блокировок email и username при регистрации;
- брокера Celery в отдельной Redis database.

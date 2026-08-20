# Схема Базы Данных (ER-диаграмма)

```mermaid
erDiagram
    USERS {
        int id PK
        varchar(LEN) username UK "NOT NULL"
        varchar(LEN) email UK "NOT NULL"
        varchar(LEN) hashed_password "NOT NULL"
        datetime created_at
        boolean is_active "NOT NULL DEFAULT: TRUE"
    }

    URLS {
        int id PK
        int user_id FK "NOT NULL UK1"
        varchar(LEN) original_url "NOT NULL UK1"
        varchar(LEN) short_url UK "NOT NULL"
        boolean is_active "NOT NULL DEFAULT: TRUE"
        datetime created_at "NOT NULL DEFAULT: NOW()"
    }
    
    VISITS {
        int id PK
        int url_id FK
        datetime clicked_at "NOT NULL DEFAULT: NOW()"
        varchar(LEN) hashed_ip "NOT NULL"
    }

    USERS ||--o{ URLS : "создает"
    URLS ||--o{ VISITS : "имеет"
```

## Описание таблиц

### Таблица `USERS` (Пользователи)

Хранит информацию о зарегистрированных пользователях системы.

- `id` — уникальный идентификатор пользователя (Primary Key).
- `username` — имя пользователя (уникальное). **Макс. длина строки: 16**
- `email` — электронная почта (уникальная). **Макс. длина строки: 255**
- `hashed_password` — хэш пароля. **Макс. длина строки: 60**
- `created_at` — дата и время регистрации пользователя.
- `is_active` — статус аккаунта (используется для блокировки/мягкого удаления).

### Таблица `URLS` (Ссылки)

Хранит созданные пользователями короткие ссылки.

- `id` — уникальный идентификатор записи (Primary Key).
- `user_id` — ID владельца ссылки (Foreign Key).
- `original_url` — исходный длинный URL-адрес. **Макс. длина строки: 4096**
- `short_url` — сгенерированный уникальный токен (короткий ID). **Макс. длина строки: 6**
- `is_active` — флаг мягкого удаления. Если `False`, ссылка недоступна (возвращает 404/410).
- `created_at` — дата и время сокращения ссылки.

> **Важно (`UK1`)**: Комбинация полей `(user_id, original_url)` имеет уникальное ограничение `UniqueConstraint`, чтобы запретить дублирование ссылок у одного и того же пользователя.

### Таблица `VISITS` (Статистика переходов)

Собирает аналитику по каждому клику на короткие ссылки авторизованных пользователей.

- `id` — уникальный идентификатор перехода (Primary Key).
- `url_id` — ID ссылки, по которой перешли (Foreign Key).
- `clicked_at` — точное дата и время клика.
- `hashed_ip` — хэшированный или анонимизированный IP-адрес посетителя. **Макс. длина строки: [указать длину]**

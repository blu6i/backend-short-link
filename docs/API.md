# API

Все API-маршруты FastAPI доступны с префиксом `/api`. JWT access и refresh токены устанавливаются в HttpOnly cookies `accessToken` и `refreshToken`.

## Health

### Проверка состояния

```http
GET /health
```

Ответ содержит состояние подключения к базе данных.

## User API

Базовый путь: `/api/users`.

### Регистрация

```http
POST /api/users/register
Content-Type: application/json
```

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "password123"
}
```

Ограничения: пароль от 8 до 64 символов, username максимум 32 символа, email должен быть корректным.

Ответ `201 Created` содержит `id`, `username`, `email` и устанавливает обе cookies.

Возможные ошибки: `409 Conflict` при занятом email/username, `422 Unprocessable Entity` при ошибке валидации.

### Вход

```http
POST /api/users/login
Content-Type: application/json
```

```json
{
  "email": "alice@example.com",
  "password": "password123"
}
```

Ответ `200 OK` устанавливает новую пару cookies. При неверных данных возвращается `400 Bad Request`.

### Текущий пользователь

```http
GET /api/users/me
Cookie: accessToken=<token>
```

Ответ `200 OK`:

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

Без действующего access token возвращается `401 Unauthorized`.

### Обновление токенов

```http
POST /api/users/refresh_token
Cookie: refreshToken=<token>
```

Ответ `200 OK` устанавливает новую пару cookies. Требуется действующий refresh token.

### Выход

```http
POST /api/users/unlogin
Cookie: accessToken=<token>
```

Ответ `204 No Content` удаляет access и refresh cookies.

## URL API

Базовый путь: `/api/urls`.

### Создание короткой ссылки

```http
POST /api/urls/
Content-Type: application/json
```

```json
{
  "original_url": "https://example.com/page"
}
```

Авторизация необязательна.

- гость получает запись только в Redis с TTL 24 часа;
- авторизованный пользователь получает запись в PostgreSQL и Redis;
- пользователь не может повторно сократить тот же URL;
- при коллизии короткого ключа выполняется до пяти попыток.

Ответ `201 Created`:

```json
{
  "original_url": "https://example.com/page",
  "short_url": "Ab12Cd"
}
```

Ошибки: `409 Conflict` при исчерпании попыток или дубликате пользовательского URL, `422 Unprocessable Entity` при неверном URL.

### Список ссылок пользователя

```http
GET /api/urls/my?page=1&per_page=10
Cookie: accessToken=<token>
```

Ответ содержит `items`, `total`, `page`, `per_page` и `total_pages`. Требуется авторизация.

### Все ссылки

```http
GET /api/urls/?page=1&per_page=10
```

Возвращает пагинированный список ссылок, сохранённых в PostgreSQL.

### Статистика ссылки

```http
GET /api/urls/{short_url}?scale=day
Cookie: accessToken=<token>
```

`short_url` должен состоять ровно из 6 символов Base62. Параметр `scale` обязателен и принимает значения `day`, `month` или `year`.

Ответ `200 OK`:

```json
{
  "short_url": "Ab12Cd",
  "scale": "day",
  "total": 3,
  "items": [
    {"period": "2026-09-06", "count": 2},
    {"period": "2026-09-07", "count": 1}
  ]
}
```

Статистика доступна только авторизованному владельцу ссылки. Возможные ошибки: `401 Unauthorized`, `404 Not Found`, `422 Unprocessable Entity`.

### Удаление ссылки

```http
DELETE /api/urls/{short_url}
Cookie: accessToken=<token>
```

Выполняет мягкое удаление пользовательской ссылки и удаляет её ключ из Redis. Ответ `204 No Content`.

## Redirect API

### Переход по короткой ссылке

```http
GET /{short_url}
```

Ответ `307 Temporary Redirect` содержит заголовок `Location` с исходным URL.

Nginx передаёт IP клиента в FastAPI через `X-Real-IP`. FastAPI отправляет короткий URL, IP и User-Agent в Celery-задачу. Worker получает геоданные через внешний API и сохраняет статистику в PostgreSQL.

Для несуществующей ссылки возвращается `404 Not Found`.

## Cookies и deployment

Настройки cookies задаются через `.env`:

```env
AUTH__COOKIE_SECURE=true
AUTH__COOKIE_SAMESITE=lax
AUTH__COOKIE_DOMAIN=example.com
```

В production используйте HTTPS и `AUTH__COOKIE_SECURE=true`. Не передавайте JWT в URL или в обычных ответах API.

import pytest


@pytest.mark.asyncio
async def test_redis_operations(fake_async_redis):
    # Тестируем запись
    assert await fake_async_redis.set("token", "secret123", ex=60) is True

    # Тестируем чтение
    token = await fake_async_redis.get("token")
    assert token == "secret123"

    # Проверяем удаление
    await fake_async_redis.delete("token")
    assert await fake_async_redis.exists("token") is False


@pytest.mark.asyncio
async def test_redis_operations_1(fake_async_redis):
    # Тестируем запись
    assert await fake_async_redis.set("123", "secret123", ex=60) is True

    # Тестируем чтение
    token = await fake_async_redis.get("123")
    assert token == "secret123"

    # Проверяем удаление
    await fake_async_redis.delete("123")
    assert await fake_async_redis.exists("123") is False

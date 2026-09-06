from io import StringIO

import pytest
from httpx import AsyncClient
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1 import url as url_api
from src.repositories.url import url_repo


def url_payload(original_url: str) -> dict[str, str]:
    return {"original_url": original_url}


@pytest.mark.asyncio
async def test_post_url(client: AsyncClient, fake_async_redis):
    response = await client.post(
        "/api/urls/", json={"original_url": "https://examplere.com/"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://examplere.com/"
    assert await fake_async_redis.get(data["short_url"]) == data["original_url"]


@pytest.mark.asyncio
async def test_invalid_post_url(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/api/urls/", json={"original_url": "examplere"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_redirect_url(client: AsyncClient, fake_async_redis, monkeypatch):
    import main

    monkeypatch.setattr(main, "async_redis", fake_async_redis)
    response = await client.post(
        "/api/urls/", json={"original_url": "https://examplere.com/"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://examplere.com/"
    short_url = data.get("short_url")
    assert short_url
    assert await fake_async_redis.get(short_url) == "https://examplere.com/"
    response = await client.get(f"/{short_url}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://examplere.com/"


@pytest.mark.asyncio
async def test_guest_reuses_short_url_for_same_original_url(
    client: AsyncClient, fake_async_redis
):
    original_url = "https://same.example.com/"
    first_response = await client.post("/api/urls/", json=url_payload(original_url))
    second_response = await client.post("/api/urls/", json=url_payload(original_url))

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["short_url"] == second_response.json()["short_url"]
    assert await fake_async_redis.get(first_response.json()["short_url"]) == original_url


@pytest.mark.asyncio
async def test_guest_gets_different_short_urls_for_different_original_urls(
    client: AsyncClient,
):
    first_response = await client.post(
        "/api/urls/", json=url_payload("https://one.example.com/")
    )
    second_response = await client.post(
        "/api/urls/", json=url_payload("https://two.example.com/")
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["short_url"] != second_response.json()["short_url"]


@pytest.mark.asyncio
async def test_guest_collision_uses_next_salt(
    client: AsyncClient, fake_async_redis, monkeypatch
):
    monkeypatch.setattr(
        url_api,
        "hashed_url",
        lambda original_url, salt="", user_id="": "AAAAAA" if not salt else "BBBBBB",
    )
    await fake_async_redis.set("AAAAAA", "https://occupied.example.com/")

    response = await client.post(
        "/api/urls/", json=url_payload("https://new.example.com/")
    )

    assert response.status_code == 201
    assert response.json()["short_url"] == "BBBBBB"


@pytest.mark.asyncio
async def test_guest_collision_exhaustion_returns_conflict(
    client: AsyncClient, fake_async_redis, monkeypatch
):
    monkeypatch.setattr(url_api, "hashed_url", lambda *args, **kwargs: "AAAAAA")
    await fake_async_redis.set("AAAAAA", "https://occupied.example.com/")

    response = await client.post(
        "/api/urls/", json=url_payload("https://new.example.com/")
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_database_error_is_logged_separately(client: AsyncClient, monkeypatch):
    captured_log = StringIO()
    sink_id = logger.add(captured_log, level="ERROR")

    registration_response = await client.post(
        "/api/users/register",
        json={
            "username": "db_error_user",
            "email": "db_error_user@example.com",
            "password": "password123",
        },
    )
    assert registration_response.status_code == 201

    async def raise_database_error(*args, **kwargs):
        raise SQLAlchemyError("database is unavailable")

    monkeypatch.setattr(url_repo, "create_url", raise_database_error)
    try:
        response = await client.post(
            "/api/urls/", json=url_payload("https://db-error.example.com/")
        )
    finally:
        logger.remove(sink_id)

    assert response.status_code == 500
    assert "database is unavailable" in captured_log.getvalue()
    assert "сохранении короткой ссылки" in captured_log.getvalue()


@pytest.mark.asyncio
async def test_invalid_get_url(client: AsyncClient, db_session: AsyncSession):
    response = await client.get("/api/urls/KSjdsa?scale=day")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_get_url_more(client: AsyncClient, db_session: AsyncSession):
    response = await client.get(f"/api/urls/KSjdsadsa")
    assert response.status_code == 401

from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1 import url as url_api
from src.core.exceptions import AlreadyExistsException
from src.repositories.user import user_repo
from src.schemas.user import UserCreateSchem


def user_payload() -> dict[str, str]:
    suffix = uuid4().hex[:8]
    return {
        "username": f"user_{suffix}",
        "email": f"{suffix}@example.com",
        "password": "password123",
    }


@pytest.mark.asyncio
async def test_register_read_login_and_logout(
    client: AsyncClient, db_session: AsyncSession
):
    payload = user_payload()

    register_response = await client.post("/api/users/register", json=payload)

    assert register_response.status_code == 201
    registered_user = register_response.json()
    assert registered_user["username"] == payload["username"]
    assert registered_user["email"] == payload["email"]
    assert "password" not in registered_user
    assert client.cookies.get("accessToken")
    assert client.cookies.get("refreshToken")

    me_response = await client.get("/api/users/me")
    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": registered_user["id"],
        "username": payload["username"],
        "email": payload["email"],
    }

    stored_user = await user_repo.get(registered_user["id"], db_session)
    assert stored_user.username == payload["username"]
    assert stored_user.email == payload["email"]

    logout_response = await client.post("/api/users/unlogin")
    assert logout_response.status_code == 204
    assert not client.cookies.get("accessToken")
    assert not client.cookies.get("refreshToken")
    assert (await client.get("/api/users/me")).status_code == 401

    login_response = await client.post(
        "/api/users/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    assert login_response.json()["id"] == registered_user["id"]
    assert client.cookies.get("accessToken")
    assert client.cookies.get("refreshToken")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"username": "short", "email": "invalid", "password": "password123"},
        {"username": "valid_user", "email": "user@example.com", "password": "short"},
        {"username": "x" * 33, "email": "user@example.com", "password": "password123"},
    ],
)
async def test_register_validation(client: AsyncClient, payload: dict[str, str]):
    response = await client.post("/api/users/register", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_validation_and_wrong_password(client: AsyncClient):
    payload = user_payload()
    register_response = await client.post("/api/users/register", json=payload)
    assert register_response.status_code == 201

    response = await client.post(
        "/api/users/login",
        json={"email": payload["email"], "password": "wrong-password"},
    )
    assert response.status_code == 400

    response = await client.post(
        "/api/users/login", json={"email": "invalid", "password": "short"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_repository_maps_integrity_error_to_conflict():
    session = Mock()
    session.add = Mock()
    session.commit = AsyncMock(
        side_effect=IntegrityError("insert", {}, Exception("duplicate"))
    )
    session.rollback = AsyncMock()

    with pytest.raises(AlreadyExistsException, match="Почта или имя уже заняты"):
        await user_repo.create(
            session, UserCreateSchem(**user_payload()), "hashed-password"
        )

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticated_user_creates_and_reads_own_url(
    client: AsyncClient, fake_async_redis
):
    payload = user_payload()
    register_response = await client.post("/api/users/register", json=payload)
    assert register_response.status_code == 201

    original_url = "https://user.example.com/"
    response = await client.post("/api/urls/", json={"original_url": original_url})

    assert response.status_code == 201
    link = response.json()
    assert link["original_url"] == original_url
    assert await fake_async_redis.get(link["short_url"]) == original_url

    response = await client.get("/api/urls/my")

    assert response.status_code == 200
    assert any(
        item["short_url"] == link["short_url"] for item in response.json()["items"]
    )


@pytest.mark.asyncio
async def test_authenticated_user_url_validation(client: AsyncClient):
    register_response = await client.post("/api/users/register", json=user_payload())
    assert register_response.status_code == 201

    response = await client.post("/api/urls/", json={"original_url": "not-a-url"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_same_url_is_unique_for_user_but_allowed_for_different_users(
    client: AsyncClient,
):
    first_user = user_payload()
    second_user = user_payload()
    original_url = "https://shared.example.com/"

    assert (await client.post("/api/users/register", json=first_user)).status_code == 201
    first_link_response = await client.post(
        "/api/urls/", json={"original_url": original_url}
    )
    assert first_link_response.status_code == 201

    duplicate_response = await client.post(
        "/api/urls/", json={"original_url": original_url}
    )
    assert duplicate_response.status_code == 409

    assert (await client.post("/api/users/unlogin")).status_code == 204
    assert (await client.post("/api/users/register", json=second_user)).status_code == 201
    second_link_response = await client.post(
        "/api/urls/", json={"original_url": original_url}
    )

    assert second_link_response.status_code == 201
    assert (
        second_link_response.json()["short_url"]
        != first_link_response.json()["short_url"]
    )


@pytest.mark.asyncio
async def test_same_url_has_separate_guest_and_user_keys(
    client: AsyncClient,
):
    original_url = "https://guest-and-user.example.com/"
    guest_response = await client.post("/api/urls/", json={"original_url": original_url})
    assert guest_response.status_code == 201

    assert (await client.post("/api/users/register", json=user_payload())).status_code == 201
    user_response = await client.post(
        "/api/urls/", json={"original_url": original_url}
    )

    assert user_response.status_code == 201
    assert user_response.json()["short_url"] != guest_response.json()["short_url"]


@pytest.mark.asyncio
async def test_user_collision_uses_next_salt(
    client: AsyncClient, fake_async_redis, monkeypatch
):
    assert (await client.post("/api/users/register", json=user_payload())).status_code == 201
    monkeypatch.setattr(
        url_api,
        "hashed_url",
        lambda original_url, salt="", user_id="": "AAAAAA" if salt == "salt_0" else "BBBBBB",
    )
    await fake_async_redis.set("AAAAAA", "https://occupied.example.com/")

    response = await client.post(
        "/api/urls/", json={"original_url": "https://new-user.example.com/"}
    )

    assert response.status_code == 201
    assert response.json()["short_url"] == "BBBBBB"


@pytest.mark.asyncio
async def test_user_collision_exhaustion_returns_conflict(
    client: AsyncClient, fake_async_redis, monkeypatch
):
    assert (await client.post("/api/users/register", json=user_payload())).status_code == 201
    monkeypatch.setattr(url_api, "hashed_url", lambda *args, **kwargs: "AAAAAA")
    await fake_async_redis.set("AAAAAA", "https://occupied.example.com/")

    response = await client.post(
        "/api/urls/", json={"original_url": "https://new-user.example.com/"}
    )

    assert response.status_code == 409
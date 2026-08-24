import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import log


@pytest.mark.asyncio
async def test_post_url(client: AsyncClient, db_session: AsyncSession):
    response = await client.post(
        "/api/urls/", json={"original_url": "https://examplere.com/"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://examplere.com/"


@pytest.mark.asyncio
async def test_invalid_post_url(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/api/urls/", json={"original_url": "examplere"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_url(client: AsyncClient, db_session: AsyncSession):
    response = await client.post(
        "/api/urls/", json={"original_url": "https://examplere.com/"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://examplere.com/"
    short_url = data.get("short_url")
    assert short_url
    response = await client.get(f"/api/urls/{short_url}")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://examplere.com/"
    assert data["short_url"] == short_url


@pytest.mark.asyncio
async def test_invalid_get_url(client: AsyncClient, db_session: AsyncSession):
    response = await client.get(f"/api/urls/KSjdsa")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_get_url_more(client: AsyncClient, db_session: AsyncSession):
    response = await client.get(f"/api/urls/KSjdsadsa")
    assert response.status_code == 422

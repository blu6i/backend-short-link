from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import main
from src.models.base import Base
from src.models.statistic_url import StatisticUrlBase
from src.models.url import UrlBase
from src.repositories.url import url_repo
from src.tasks import statistics
from src.utils.hashed import hash_ip


@pytest.mark.asyncio
async def test_redirect_enqueues_click_statistics(
    client, fake_async_redis, monkeypatch
):
    short_url = "Ab12Cd"
    original_url = "https://redirect.example.com/"
    await fake_async_redis.set(short_url, original_url)
    queued_task = Mock()
    monkeypatch.setattr(main, "async_redis", fake_async_redis)
    monkeypatch.setattr(main.process_click_task, "delay", queued_task)

    response = await client.get(
        f"/{short_url}",
        headers={"user-agent": "pytest-agent"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == original_url
    queued_task.assert_called_once_with(
        short_url=short_url,
        ip="127.0.0.1",
        user_agent="pytest-agent",
    )


@pytest.mark.asyncio
async def test_redirect_uses_real_ip_header(
    client, fake_async_redis, monkeypatch
):
    short_url = "Ip12Ab"
    await fake_async_redis.set(short_url, "https://ip.example.com/")
    queued_task = Mock()
    monkeypatch.setattr(main, "async_redis", fake_async_redis)
    monkeypatch.setattr(main.process_click_task, "delay", queued_task)

    response = await client.get(
        f"/{short_url}",
        headers={"user-agent": "pytest-agent", "x-real-ip": "198.51.100.7"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    queued_task.assert_called_once_with(
        short_url=short_url,
        ip="198.51.100.7",
        user_agent="pytest-agent",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scale", "expected_periods", "expected_counts"),
    [
        ("day", ["2026-01-02", "2026-02-03"], [2, 1]),
        ("month", ["2026-01-01", "2026-02-01"], [2, 1]),
        ("year", ["2026-01-01"], [3]),
    ],
)
async def test_get_url_returns_aggregated_statistics(
    client,
    db_session,
    scale: str,
    expected_periods: list[str],
    expected_counts: list[int],
):
    suffix = uuid4().hex[:8]
    user_payload = {
        "username": f"statistics_{suffix}",
        "email": f"statistics_{suffix}@example.com",
        "password": "password123",
    }
    register_response = await client.post("/api/users/register", json=user_payload)
    assert register_response.status_code == 201
    create_response = await client.post(
        "/api/urls/", json={"original_url": "https://statistics.example.com/"}
    )
    assert create_response.status_code == 201
    short_url = create_response.json()["short_url"]
    url = await url_repo.get_url(db_session, short_url)

    for clicked_at in (
        datetime(2026, 1, 2, 10),
        datetime(2026, 1, 2, 11),
        datetime(2026, 2, 3, 12),
    ):
        db_session.add(
            StatisticUrlBase(
                url_id=url.id,
                clicked_at=clicked_at,
                hashed_ip="hashed",
                user_agent="pytest",
            )
        )
    await db_session.flush()

    response = await client.get(f"/api/urls/{short_url}?scale={scale}")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "short_url": short_url,
        "scale": scale,
        "total": 3,
        "items": [
            {"period": period, "count": count}
            for period, count in zip(expected_periods, expected_counts)
        ],
    }


@pytest.mark.asyncio
async def test_get_url_statistics_rejects_unknown_scale(client):
    suffix = uuid4().hex[:8]
    register_response = await client.post(
        "/api/users/register",
        json={
            "username": f"scale_{suffix}",
            "email": f"scale_{suffix}@example.com",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201

    response = await client.get("/api/urls/Ab12Cd?scale=week")

    assert response.status_code == 422


def test_click_task_stores_statistics_in_database(tmp_path: Path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'statistics.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(statistics, "SyncSessionLocal", session_factory)

    with session_factory() as session:
        url = UrlBase(original_url="https://stored.example.com/", short_url="St1234")
        session.add(url)
        session.commit()
        url_id = url.id

    geo_response = Mock()
    geo_response.raise_for_status.return_value = None
    geo_response.json.return_value = {"country": "RU", "city": "Moscow"}
    monkeypatch.setattr(statistics.requests, "get", Mock(return_value=geo_response))

    statistics.process_click_task.run("St1234", "192.0.2.10", "pytest-agent")

    with Session(engine) as session:
        stat = session.scalar(
            select(StatisticUrlBase).where(StatisticUrlBase.url_id == url_id)
        )

    assert stat is not None
    assert stat.hashed_ip == hash_ip("192.0.2.10")
    assert stat.user_agent == "pytest-agent"
    assert stat.country == "RU"
    assert stat.city == "Moscow"
    assert statistics.process_click_task.rate_limit == "3/s"

    engine.dispose()


def test_click_task_does_not_call_geo_api_for_missing_url(tmp_path: Path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'missing.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(statistics, "SyncSessionLocal", session_factory)
    geo_request = Mock()
    monkeypatch.setattr(statistics.requests, "get", geo_request)

    statistics.process_click_task.run("Missing", "192.0.2.10", "pytest-agent")

    geo_request.assert_not_called()
    engine.dispose()

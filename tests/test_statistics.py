from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import main
from src.models.base import Base
from src.models.statistic_url import StatisticUrlBase
from src.models.url import UrlBase
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

"""Таск для ведения статистики."""

import requests
from sqlalchemy import select

from src.core.celery_app import SyncSessionLocal, celery_app
from src.core.logger import log
from src.core.settings import settings
from src.models.statistic_url import StatisticUrlBase
from src.models.url import UrlBase
from src.utils.hashed import hash_ip


@celery_app.task(bind=True, max_retries=3, rate_limit="3/s")
def process_click_task(self, short_url: str, ip: str, user_agent: str):
    """
    Статистика переходов по ссылке.

    Args:
        short_url (str): short url из бд, по которой перешли
        ip (str): ip, который перешел
        user_agent (str): user agent пользователя

    Raises:
        self.retry: попытка ретраить подключения к внешнему АПИ

    """
    try:
        with SyncSessionLocal() as session:
            stmt = select(UrlBase).where(UrlBase.short_url == short_url)
            url = session.scalar(stmt)
            if not url:
                return
            url_id = url.id
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

    country = None
    city = None
    try:
        response = requests.get(
            f"https://api.2ip.io/{ip}?token={settings.api_token.ip_checked}", timeout=5
        )
        response.raise_for_status()
        data = response.json()
        log.debug(data)
        country = data.get("country")
        city = data.get("city")

    except requests.RequestException as exc:
        raise self.retry(exc=exc, countdown=60)

    try:
        with SyncSessionLocal() as session:
            stat = StatisticUrlBase(
                url_id=url_id,
                hashed_ip=hash_ip(ip),
                user_agent=user_agent,
                country=country,
                city=city,
            )
            session.add(stat)
            session.commit()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

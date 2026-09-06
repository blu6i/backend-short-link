"""Модуль для хэширования ссылок."""

import hashlib
from hashlib import md5

from base62 import encodebytes

from src.core.logger import log
from src.core.settings import settings

LEN_SHORT_URL = 6


def hashed_url(original_url: str, salt: str = "", user_id: str = "") -> str:
    """
    Хэширует оригинальную ссылку.

    Args:
        original_url (str): оригинальная ссылка.
        salt (str): соль для хэширования. default="".
        user_id (str): id пользователя, чью ссылку хэшируем

    Returns:
        str: Хэшированная ссылка длиной 6.

    """
    data = (original_url + salt + user_id).encode()
    url_md5 = md5(data).digest()
    url_base62 = encodebytes(url_md5)
    return url_base62[:LEN_SHORT_URL]


def hash_ip(ip: str) -> str:
    """
    Хэширует IP.

    Args:
        ip (str): IP для хэша

    Returns:
        str: результат хэширования

    """
    pepper = settings.salt.hashed_ip_salt
    data = (ip + pepper).encode("utf-8")

    # Хэшируем и возвращаем строку
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    log.debug(hashed_url("jhhsdnbfjsdnfj.kajf"))

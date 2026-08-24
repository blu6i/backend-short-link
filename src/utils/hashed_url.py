"""Модуль для хэширования ссылок."""

import datetime
from hashlib import md5

from base62 import encodebytes

from src.core.logger import log

LEN_SHORT_URL = 6


def hashed_url(original_url: str, salt: str = "") -> str:
    """
    Хэширует оригинальную ссылку.

    Args:
        original_url (str): оригинальная ссылка.
        salt (str): соль для хэширования. default="".

    Returns:
        str: Хэшированная ссылка длиной 6.

    """
    # TODO: вместо генерации датавремя и соли приписывать ИД пользователя, если он есть
    data = (original_url + salt + str(datetime.datetime.now(datetime.UTC))).encode()
    url_md5 = md5(data).digest()
    url_base62 = encodebytes(url_md5)
    return url_base62[:LEN_SHORT_URL]


if __name__ == "__main__":
    log.debug(hashed_url("jhhsdnbfjsdnfj.kajf"))

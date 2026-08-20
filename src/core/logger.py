"""Настройка централизованного логирования приложения через Loguru."""

import os
import sys
from pathlib import Path

from loguru import logger

from src.core.settings import LogSettings, settings


class AppLogger:
    """
    Централизованный класс для настройки логирования через Loguru.

    Использует singleton-паттерн, чтобы логгер настраивался только один раз.
    """

    _instance = None  # Храним единственный экземпляр класса

    def __new__(cls, *args, **kwargs):
        """Создаёт единственный экземпляр класса логгера."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: LogSettings):
        """
        Инициализирует логгер заданными настройками.

        Args:
            settings: Настройки уровня, ротации и хранения логов.

        """
        # Защита от повторной инициализации (важно для singleton)
        if getattr(self, "_initialized", False):
            return

        self._settings = settings
        self._setup_logger()

        self._initialized = True

    def _setup_logger(self):
        """Настраивает консольный и файловый вывод логов."""
        # Определяем корневую директорию проекта
        base_dir = Path(__file__).resolve().parent.parent.parent

        # Папка для логов (../log)
        log_dir = base_dir / "log"

        # Создаём папку, если она отсутствует
        os.makedirs(log_dir, exist_ok=True)

        # Удаляем стандартные обработчики loguru
        logger.remove()

        log_format = self._settings.log_format

        # -----------------------------
        # Консольный вывод
        # -----------------------------
        logger.add(
            sink=sys.stdout,
            level=self._settings.log_level,
            format=log_format,
        )

        # -----------------------------
        # Файловый вывод
        # -----------------------------
        logger.add(
            sink=log_dir / "app_{time:YYYY-MM-DD}.log",
            level=self._settings.log_level,
            format=log_format,
            rotation=self._settings.log_rotation,
            retention=self._settings.log_retention,
            compression="zip",
            encoding="utf-8",
        )

    @property
    def get_logger(self):
        """Возвращает настроенный экземпляр Loguru."""
        return logger


app_logger = AppLogger(settings.log)
log = app_logger.get_logger

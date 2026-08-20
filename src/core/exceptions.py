"""Пользовательские исключения приложения и их HTTP-статусы."""

from fastapi import status


class AppException(Exception):
    """
    Базовое исключение для всего приложения.

    Все пользовательские исключения должны наследоваться от этого класса.
    """

    def __init__(
        self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """Создаёт исключение с сообщением и HTTP-статусом."""
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    """Возникает при отсутствии запрашиваемого ресурса в системе."""

    def __init__(self, message: str = "Ресурс не найден"):
        """Создаёт исключение с сообщением об отсутствии ресурса."""
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class AlreadyExistsException(AppException):
    """Возникает при попытке создать дубликат уникальной сущности."""

    def __init__(self, message: str = "Ресурс уже существует"):
        """Создаёт исключение с сообщением о существующем ресурсе."""
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class PermissionDeniedException(AppException):
    """Возникает при попытке выполнить действие без необходимых прав."""

    def __init__(self, message: str = "Доступ запрещен"):
        """Создаёт исключение с сообщением о недостаточных правах."""
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class UnauthorizedException(AppException):
    """Возникает при отсутствии или недействительности авторизации."""

    def __init__(self, message: str = "Необходима авторизация"):
        """Создаёт исключение с сообщением о необходимости авторизации."""
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)

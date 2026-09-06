"""Репозиторий для модели пользователя."""

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AlreadyExistsException, NotFoundException
from src.core.logger import log
from src.models.user import UserBase
from src.schemas.user import UserCreateSchem, UserLoginShem


class UserRepository:
    """Репозитория для модели пользователя."""

    def __init__(self, model: type[UserBase]) -> None:
        """Инициализация репозитория."""
        self.model = model

    async def get(self, id: int, session: AsyncSession) -> UserBase:
        """Возвращает пользователя по ИД."""
        user = await session.get(self.model, id)
        if not user:
            raise NotFoundException(message="Пользователь не найден")
        return user

    async def create(
        self, session: AsyncSession, user_data: UserCreateSchem, hash_password: str
    ) -> UserBase:
        """
        Создание пользователя.

        Args:
            session (AsyncSession): сессия бд
            user_data (UserCreateSchem): данные пользователя
            hash_password (str): хэш пароля

        Returns:
            UserBase: модель пользователя

        """
        user = self.model(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hash_password,
        )
        session.add(user)
        try:
            await session.commit()
            return user
        except IntegrityError as error:
            await session.rollback()
            log.exception("Ошибка БД при создании пользователя")
            raise AlreadyExistsException("Почта или имя уже заняты") from error

    async def get_by_email(self, session: AsyncSession, email: str) -> UserBase:
        """
        Возвращает пользователя по почте.

        Args:
            session (AsyncSession): сессия БД
            email (str): почта пользователя

        Raises:
            NotFoundException: пользователь по почте не найден

        Returns:
            UserBase: данные пользователя

        """
        stmt = select(self.model).where(self.model.email == email)
        result = await session.scalar(stmt)
        if not result:
            raise NotFoundException
        return result


user_repo = UserRepository(UserBase)

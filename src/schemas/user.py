"""Схема для пользователя."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserReadSchem(BaseModel):
    """Схема чтения пользователя."""

    id: int
    username: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class UserCreateSchem(BaseModel):
    """Схема создания пользователя."""

    username: Annotated[str, Field(..., max_length=32)]
    email: Annotated[EmailStr, Field(..., max_length=255)]
    password: Annotated[str, Field(..., min_length=8, max_length=64)]


class UserUpdateSchem(BaseModel):
    """Схема обновления пользователя."""

    username: Annotated[str | None, Field(max_length=32)]
    email: Annotated[EmailStr | None, Field(max_length=255)]
    password: Annotated[str | None, Field(min_length=8, max_length=64)]


class UserLoginShem(BaseModel):
    """Схема логина пользователя."""

    email: Annotated[EmailStr, Field(..., max_length=255)]
    password: Annotated[str, Field(..., min_length=8, max_length=64)]

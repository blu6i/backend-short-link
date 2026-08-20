"""Шаблон CRUD-роутера для ресурсов версии API v1."""

from typing import TypeVar

from fastapi import APIRouter, status

router = APIRouter(prefix="templates", tags=["tmp", "temp"])

ResponseModel = TypeVar("ResponseModel")


@router.get("/{id}", response_model=ResponseModel)
async def get_item(id: int):
    """Возвращает ресурс по его идентификатору."""
    return {"messages": "hello world"}


@router.get("/", response_model=list[ResponseModel])
async def get_items():
    """Возвращает список ресурсов."""
    return {"messages": "hello world"}


@router.patch("/{id}", response_model=ResponseModel)
async def update_field_item(id: int):
    """Частично обновляет ресурс по его идентификатору."""
    return {"messages": "hello world"}


@router.put("/{id}", response_model=ResponseModel)
async def update_all_field_item(id: int):
    """Полностью обновляет ресурс по его идентификатору."""
    return {"messages": "hello world"}


@router.post("/", response_model=ResponseModel)
async def create_item():
    """Создаёт новый ресурс."""
    return {"messages": "hello world"}


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(id: int):
    """Удаляет ресурс по его идентификатору."""
    pass

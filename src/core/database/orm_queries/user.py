import logging
from typing import Optional
from sqlalchemy import select, update, delete, exists
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.models.models import User, Product, Category, Cart, Banner

"""Модуль для работы с пользователями.

Содержит функции для:
- Добавления новых пользователей
- Управления статусами пользователей
- Удаления пользователей
- Проверки данных пользователей
"""


async def orm_add_user(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    first_name: str,
    is_active: bool = True,
    is_admin: bool = False,
    ) -> bool:
    """Добавляет нового пользователя в бд"""
    try:
        # Проверяем существование пользователя 
        user_exists = await session.scalar(
                select(exists().where(User.user_id == user_id)))

        if user_exists:
            logging.info(f" Пользователь {user_id} уже есть в базе данных")
            return False

        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            is_active=is_active,
            is_admin=is_admin,
        ) 

        session.add(user)
        await session.commit()
        logging.info(f"Успешно добавлен пользователь {user_id}")
        return True

    except Exception as e:
        await session.rollback()
        logging.error(f" Ошибка добавления пользователя в БД: {e}")
        return False

async def orm_change_active(session: AsyncSession, user_id: str, is_active: bool) -> None:
    """Изменяет статус активности пользователя"""
    await session.execute(update(User).filter(User.user_id == user_id)).values(is_active=is_active)
    await session.commit()

async def orm_delete_user(session: AsyncSession, user_id: int) -> None:
    """Полностью удаляет пользователя из бд"""
    await session.execute(delete(User).where(User.user_id == user_id))
    await session.commit()

async def orm_select_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Получает данные пользователя по ID"""
    return await session.scalar(select(User).where(User.user_id == user_id))

async def orm_ban_status_user(session: AsyncSession, user_id: int, new_status: bool) -> None:
    """Изменяет статус бана пользователя"""
    await session.execute(update(User).where(User.user_id == user_id).values(banned=new_status))
    await session.commit()

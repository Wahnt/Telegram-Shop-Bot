from sqlalchemy import select, update, delete, exists, and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.models.models import User


async def get_all_active_users(session: AsyncSession) -> list:
    """Получает ID всех пользователей с активным(True) полем is_active"""
    query = await session.execute(select(User.user_id).where(User.is_active == True))
    return query.scalars().all()


async def update_users_status(
    session: AsyncSession, success_ids: list[int], blocked_ids: list[int]
) -> None:
    """Обновляет статусы пользователей, которые заблокировали бота"""

    if blocked_ids:
        await session.execute(
            update(User).where(
                User.user_id.in_(blocked_ids)).values(
                is_active=False)
        )

    await session.commit()
    await session.rollback()
    return

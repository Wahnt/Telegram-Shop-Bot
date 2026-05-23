from sqlalchemy import select, update, delete, exists, and_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.models.models import User, Payment, Purchase, PurchaseItem

"""В этом модуле написаны все запросы, связанные с администрацией
 - Административные статусы
 - 1 - активный(Может принимать запросы от пользователей)
 - 2 - оказывает поддержку пользователю через чат внутри бота, находится в сессии
 - 3 - не активный, пользователь не может связаться с данныи администратором

"""

async def orm_add_admin(
    session: AsyncSession,
    user_id: int,
    is_admin: bool,
    admin_status: int
    ):
	"""Добавляет администратора в бд"""
	await session.execute(update(User).where(User.user_id == user_id).values(
        is_admin=is_admin,
        admin_status=admin_status))
	await session.commit()

async def orm_change_status_admin(
    session: AsyncSession, user_id: int, admin_status: int):
	"""Изменяет статус администратора на противоположный"""
	await session.execute(update(User).where(User.user_id == user_id).values(admin_status=admin_status))
	await session.commit()
	return True

async def orm_get_status_admin(session: AsyncSession, user_id: int):
	"""Просмотр статуса администратора"""
	status = await session.scalar(select(User.admin_status).where(User.user_id == user_id))
	await session.commit()
	return status

async def orm_get_all_admins(session: AsyncSession):
	"""Получает всех администраторов с активным статусом"""
	res = select(User.user_id).where(User.admin_status == 1)
	result = await session.scalars(res)
	admins = result.all()
	return admins

async def get_user_with_relations(session: AsyncSession,
									user_id: int | None = None,
									username: str | None = None,) -> User | None:
	"""Получает данные пользователя, когда администратор находится в чате с оным пользователем,
		подгружает список платежей и покупок"""
	
	query = select(User).options(
		selectinload(User.payments).options(
			selectinload(Payment.purchases).options(
				selectinload(Purchase.purchases_items).options(
					joinedload(PurchaseItem.product)
				)
			)
		),
		
		selectinload(User.purchases).options(
			selectinload(Purchase.purchases_items).options(
				joinedload(PurchaseItem.product)
			)
		)
	)

	if user_id is not None:
		query = query.where(User.user_id == user_id)
	elif username is not None:
		query = query.where(User.username == username)

	result = await session.execute(query)
	return result.scalar_one_or_none()

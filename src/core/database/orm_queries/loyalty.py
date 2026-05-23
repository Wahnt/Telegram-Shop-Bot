from typing import Optional, List
from sqlalchemy import select, update, delete, exists, and_, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.models.models import Promocode, PromocodeUsage

"""Модуль для работы с промокодами.

Содержит функции для:
- Администрирования промокодов (создание, деактивация, просмотр)
- Обработки пользовательских промокодов (проверка, активация)
"""


async def orm_add_promocode(session: AsyncSession, data: dict) -> None:
	"""Добавляет новый промокод в базу данных"""
	code = Promocode(
        code=data["name"],
        description=data["description"],
        discount_type=data["discount_type"],
        discount_value=float(data["discount_value"]),
        usage=int(data["usage"]),
    )
	session.add(code)
	await session.commit()

async def orm_deactivate_promocode(session: AsyncSession, promocode_id : int) -> bool:
	"""Переключает статус активности промокода"""
	promocode = await session.get(Promocode, promocode_id)
	if not promocode:
		return None

	new_status = not promocode.is_active
	code = (
		update(Promocode)
		.where(Promocode.id == promocode_id)
		.values(is_active=new_status)
		)
	result = await session.execute(code)
	await session.commit()

async def orm_get_all_promocodes(session: AsyncSession) -> List[Promocode]:
	"""Получает список всех промокодов"""
	query = select(Promocode)
	result = await session.execute(query)
	promocodes = result.scalars().all()
	return promocodes

# Пользовательская функции
async def orm_get_user_promocode(session: AsyncSession, user_id: int) -> Optional[Promocode]:
	"""Получает активный промокод пользователя"""
	query = await session.execute(
		select(Promocode)
		.join(PromocodeUsage, PromocodeUsage.promocode_id == Promocode.id)
		.where(
			and_(
				PromocodeUsage.user_id == user_id,
				Promocode.discount_type.in_(["individual", "group"]),
				PromocodeUsage.status_usage == True
			)
		)
		.order_by(PromocodeUsage.id.desc())
		.limit(1)
	)

	return query.scalar_one_or_none()

async def orm_send_promocode(session: AsyncSession, user_input: str, user_id: int) -> Optional[Promocode]:
	"""Активирует промокод для пользователя"""
	query = await session.execute(
		select(Promocode)
		.where(
			and_(Promocode.code == user_input,
				Promocode.is_active == True,
				or_(
					Promocode.usage == None,
					Promocode.usage > 0
				)
			)
		)
	)
	promocode = query.scalar_one_or_none()

	if not promocode:
		return None

	usage_query = await session.execute(
		select(PromocodeUsage)
		.where(
			and_(PromocodeUsage.user_id == user_id,
				PromocodeUsage.promocode_id == promocode.id,
				PromocodeUsage.status_usage == False
			)
		)
	)
	if usage_query.scalar_one_or_none():
		return None

	# Usage - 1
	if promocode.usage is not None and promocode.usage > 0:
		promocode.usage -= 1
		if promocode.usage <= 0:
			promocode.is_active = False

	new_usage = PromocodeUsage(
		user_id=user_id,
		promocode_id=promocode.id)

	session.add(new_usage)
	await session.commit()
	return promocode


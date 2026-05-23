from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.core.database.models.models import User, ChatSession

"""Модуль для работы с чат-сессиями пользователей
Содержит функции для:
- Создания и управления чат-сессиями между пользователями и администраторами
- Обновления статусов администраторов
- Получение информации о текущих сессиях"""


async def create_new_session_user(
    session: AsyncSession, user_id: int, username: str, first_name: str, admin_id: int) -> None:
	"""Создает новую чат-сессию для пользователя со статусом waiting, полем admin_id=0"""
	new_session = ChatSession(
			user_id=user_id,
			status="waiting",
			username=username,
			first_name=first_name,
			admin_id=admin_id
		)
	session.add(new_session)
	await session.commit()


async def get_active_chat_admin(session: AsyncSession) -> Optional[int]:
	"""Получает ID одного активного администратора"""
	res = select(User.user_id).where(User.admin_status == 1).limit(1)
	result = await session.scalar(res)
	return result

async def get_waiting_session_and_update(session: AsyncSession, user_id: int) -> Optional[ChatSession]:
	"""Находит ожидающую сессию и назначает ей администратора"""
	chat_session=(
		select(ChatSession)
		.where(ChatSession.status == 'waiting')
		.order_by(ChatSession.id)
		.limit(1)
	)

	result = await session.execute(chat_session)
	waiting_session = result.scalar_one_or_none()

	# Обновляем статус сессии
	waiting_session.status = 'active'
	waiting_session.admin_id = user_id
	session.add(waiting_session)
	await session.commit()

	admin_status = await session.execute(
		update(User)
		.where(User.user_id == user_id)
		.values(admin_status=2)
		)
	await session.commit()


	# Получаем данные пользователя
	await session.refresh(waiting_session, ['user'])

	return waiting_session

async def delete_session_user(session: AsyncSession, user_id: int, admin_id: int) -> None:
	"""Удаляет сессию и меняет статус администратора"""
	result = await session.execute(
		delete(ChatSession)
		.where(ChatSession.user_id == user_id)
	)
	await session.commit()

	# Обновлем статус администратора
	admin_status = await session.execute(
		update(User)
		.where(User.user_id == admin_id)
		.values(admin_status=1)
		)
	await session.commit()
     
async def get_admin_id_message(session: AsyncSession) -> int:
	"""Получает ID любого администратора вне зависимости от статуса"""
	res = await session.scalar(select(User.user_id).where(User.is_admin == True))
	await session.commit()
	return res 

async def get_id_support(session: AsyncSession, second_id: int, is_admin: bool = False) -> int:
	"""Получает ID собеседника(админ-пользователель и наоборот) в чат-сессии"""
	if is_admin:
		query = select(ChatSession.user_id).where(
			ChatSession.admin_id == second_id)
	else:
		query = select(ChatSession.admin_id).where(
			ChatSession.user_id == second_id)
	return await session.scalar(query)

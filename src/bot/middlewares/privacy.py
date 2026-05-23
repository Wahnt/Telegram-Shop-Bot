from sqlalchemy import select
from typing import Union, Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject, CallbackQuery
from src.core.database.models.models import User
from src.bot.filters.chat_types import ChatTypeFilter, IsAdmin
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.cache.cache import CacheService

"""Модуль Мидлварь 'Privacy'
- Проверяет наличие согласия пользователя в кэше, затем в бд
- """

ALERT_TEXT = " для использования бота, а также продуктов, купленных через интерфейс бота необходимо принять условия конфиденциальности."


class PrivacyConsentMiddleware(BaseMiddleware):
    def __init__(self, cache: CacheService):
        # Доступные команды для пользователя
        self.exemp_commands = {"/start", "/info"}
        self.allowed_callbacks = {"accept_"}
        self.cache = cache

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Вызвод мидлваря, пропускает через себя все виды апдейтов"""
        bot: Optional[Bot] = data.get("bot")
        session: Optional[AsyncSession] = data.get("session")
        # Игнорируем системные апдейты
        if not bot or not session:
            return await handler(event, data)
        # Устанавливаем принадлежность апдейта callback
        if isinstance(event, CallbackQuery):
            return await self.handle_callback(event, handler, data)
        # Принадлежность к типам message - сообщение или команда
        elif isinstance(event, Message):
            return await self.handle_message(event, handler, data)

        return await handler(event, data)

    async def handle_message(
        self, event: Message, handler: Callable, data: Dict[str, Any]
    ) -> Any:
        # Пропускаем доступные команды
        command = self.extract_command(event.text)

        if command in self.exemp_commands:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            raise RuntimeError("AsyncSession not found")

        if not await self.check_user_consent(session, event.from_user.id):
            await event.answer(f"@{event.from_user.username},{ALERT_TEXT}")
            return
        return await handler(event, data)

    async def handle_callback(
        self, event: CallbackQuery, handler: Callable, data: Dict[str, Any]
    ) -> Any:

        if event.data in self.allowed_callbacks:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            raise RuntimeError("AsyncSession not found")

        if not await self.check_user_consent(session, event.from_user.id):
            await event.answer("⛔ Отказано в доступе.", show_alert=True)
            return

        return await handler(event, data)

    async def check_user_consent(
            self, session: AsyncSession, user_id: int) -> bool:
        """Проверяет согласие в кэшэ и в бд"""
        cached_consent = await self.cache.get_user_consent(user_id)
        if cached_consent is not None:
            return cached_consent

        result = await session.execute(
            select(User.accepted_privacy).where(User.user_id == user_id)
        )
        has_consent = bool(result.scalar_one_or_none())

        await self.cache.cache_user_consent(user_id, has_consent)

        return has_consent

    def extract_command(self, text: Optional[str]) -> str:
        """Возвращает отредактированную строку, введеную пользователем"""

        if not text or not text.startswith("/"):
            return ""
        return text.split()[0].split("@")[0].lower()

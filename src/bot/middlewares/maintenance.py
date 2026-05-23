from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Any, Awaitable, Callable, Dict, Optional
from src.bot.filters.chat_types import IsAdmin

"""Мидлварь для технического обслуживания бота, пропускает только системные апдейты и апдейты от админа"""

MAINTENANCE_TEXT = (
    "🔧 Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже."
)


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot: Optional[Bot] = data.get("bot")
        state = data.get("state")

        # Если апдейт системный - пропускаем
        if not bot or not state:
            return await handler(event, data)

        is_admin = await IsAdmin()(event, data)
        if is_admin:
            return await handler(event, data)

        state_data = await state.get_data()
        maintenace_mode = state.get("maintenace_mode", False)
        if maintenace_mode == False:
            return await self._handle_maintenance(event)

        return await handler(event, data)

    async def _handle_maintenance(
            self, event: Message | CallbackQuery) -> None:
        if isinstance(event, Message):
            await event.answer(MAINTENANCE_TEXT)
        elif isinstance(event, CallbackQuery):
            await event.answer(MAINTENANCE_TEXT, show_alert=True)

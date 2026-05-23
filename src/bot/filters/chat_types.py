from aiogram.filters import Filter
from aiogram import Bot, types
from os import getenv


class ChatTypeFilter(Filter):
    """Фильтр для проверки типа чата"""

    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type in self.chat_types


class IsAdmin(Filter):
    """Фильтр для проверки алминистрации бота"""

    def __init__(self) -> None:
        pass

    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        return message.from_user.id in bot.my_admins_list
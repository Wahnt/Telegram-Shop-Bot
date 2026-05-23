from os import getenv
from string import punctuation

from aiogram import Bot, types, Router
from aiogram.filters import Command

from src.bot.filters.chat_types import ChatTypeFilter
from src.bot.bot_data.restricted_words import restricted_words
from src.bot.bot_data.bot_cmd_list import admin_commands

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.orm_queries.admin import orm_add_admin

"""В этом роутере мы добавляем админа бота, а также мониторим чаты групп на наличие мата/рекламы"""

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(["group", "supergroup"]))
user_group_router.edited_message.filter(
    ChatTypeFilter(["group", "supergroup"]))

@user_group_router.message(Command("admin"))
async def get_admins(message: types.Message, session: AsyncSession, bot: Bot):
    """Добавляет администратора группы в список админитсратора бота
    - Администратор бота = Администратор группы"""
    admins_list = await message.bot.get_chat_administrators(message.chat.id)

    admins_list = [
        member.user.id
        for member in admins_list
        if member.status in ("creator", "administrator")
    ]
    bot.my_admins_list = admins_list
    if message.from_user.id in admins_list:
        await orm_add_admin(session, message.from_user.id, True, 0)
        await bot.set_my_commands(
            commands=admin_commands,
            scope=types.BotCommandScopeChatMember(
                chat_id=message.chat.id, user_id=message.from_user.id
            ),
        )
    await message.delete()


def clean_text(text: str):
    """Форматирует сообщения"""
    return text.translate(str.maketrans("", "", punctuation))


# Провекра сообщений в группе
@user_group_router.edited_message()
@user_group_router.message()
async def cleaner(message: types.Message):
    if message.text is None:
        await message.delete()

    if restricted_words.intersection(clean_text(message.text.lower()).split()):
        await message.answer(
            f"{message.from_user.username}, обратитесь, пожалуйста, к администратору группы и не ругайтесь в чате."
        )
        await message.delete()
        # await message.chat.ban(message.from_user.id)

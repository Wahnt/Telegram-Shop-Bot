import asyncio
from aiogram import F, types, Router, Bot
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters import CommandStart, Command, or_f
from aiogram.utils.formatting import (
    as_list,
    as_marked_section,
    Bold,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.orm_queries.user import orm_add_user, orm_delete_user



from src.bot.filters.chat_types import ChatTypeFilter

from src.bot.handlers.kbds.inline import get_callback_btns
from src.bot.handlers.kbds.reply import get_keyboard
from src.core.cache.cache import cache

'''Роутер для принятия соглашений(Оферта,Обратботка персональных данных, полити конфиденциальности), если подтверждения нет, пользователь
      не может использовать бота, мидлварь не пропустит апдейты, кроме команды /start , /info '''

user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))

COMBINED_AGREEMENT_TEXT = """
📜 <b>Юридические условия использования телеграм-бота</b>
"""

INFO_TEXT = """__
"""


@user_private_router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обрабатывает команду /start
    -Возвращает сообщение с юр. информацией и кнопкой Принять"""
    await message.answer(text=COMBINED_AGREEMENT_TEXT,
                         reply_markup=get_callback_btns(btns={"Принять ✅": f"accept_"}))


@user_private_router.callback_query(F.data.startswith("accept_"))
async def cmd_accept(callback: types.CallbackQuery,
                     session: AsyncSession, bot: Bot):
    """Обрабатывает согласие пользователя, добавляет в бд и создает кеш на согласие"""
    await callback.answer()
    user_id = callback.from_user.id
    await orm_add_user(session,
                       user_id,
                       callback.from_user.username,
                       callback.from_user.first_name,)
    await cache.cache_user_consent(user_id, True)
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await callback.message.answer(text=INFO_TEXT, reply_markup=get_callback_btns(btns={"Перейти в магазин": "shop"}))


@user_private_router.message(Command("info"))
async def cmd_info(message: types.Message):
    """Возвращает сообщение с юр. информацией"""
    await message.answer(text=COMBINED_AGREEMENT_TEXT, reply_markup=get_callback_btns(btns={"Перейти в магазин": "shop"}))


@user_private_router.message(Command("revoke_consent"))
async def cmd_revoke_consent(message: types.Message):
    """Обрабаытвает запрос пользователя на отзыв согласия"""
    await message.answer(f"Хотите удалить ваши персональные данные?\
                                                \nДальнейшее использование бота станет <b>недоступным</b>\
                  \nТакже если вы совершали покупки через интерфейс бота, данные о платежах и покупках тоже будут удалены.", reply_markup=get_callback_btns(btns={"Удалить": "del_"}))


@user_private_router.callback_query(F.data.startswith("del_"))
async def cmd_delete_consent(
        callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    """Обрабаытвает удаление согласия пользователя, удаляет пользователя из БД, каскадное удаление"""
    user_id = callback.from_user.id
    await orm_delete_user(session, user_id)
    await cache.invalidate_user_consent(user_id)
    await callback.answer(f"Ваши данные удалены.", show_alert=True)

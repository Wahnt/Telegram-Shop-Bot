from datetime import datetime
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.types.callback_query import CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.orm_queries.user import (
    orm_select_user,
    orm_ban_status_user,
)

from src.bot.filters.chat_types import ChatTypeFilter, IsAdmin

from src.bot.handlers.kbds.admin.inline_admin import AdminCallback, get_admin_main_btn

"""Модуль для работы с административными командами бота для главного админа.

Содержит обработчики для:
- Блокировки/разблокировки пользователей
- Отправки сообщений пользователям
"""

admin_main_router = Router()
admin_main_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_MAIN_KB = get_admin_main_btn()


class CommandAction(StatesGroup):
    # Banned
    waiting_for_user_id = State()
    waiting_for_reason = State()

    # Unbanned
    waiting_for_unbaned = State()

    # Connect with user
    waiting_for_message = State()
    waiting_for_send_message = State()


@admin_main_router.message(Command("ban"))
async def cmd_banned(message: types.Message, state: FSMContext) -> None:
    """Запрашивает ID пользователя"""
    await message.answer("Введите ID пользователя, которого хотите забанить\nДля выхода напишите: <b>'отмена'</b>")
    await state.set_state(CommandAction.waiting_for_user_id)


@admin_main_router.message(CommandAction.waiting_for_user_id, F.text)
async def cmd_check_banned_user_id(
    message: types.Message, state: FSMContext, session: AsyncSession):
    """Проверяет ID пользователя"""
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("<b>Действия отменены</b>", reply_markup=ADMIN_MAIN_KB)
        return

    if not message.text.isdigit():
        await message.answer("Введите корректный числовой id")
        return

    user_id = int(message.text)
    user = await orm_select_user(session, user_id=user_id)

    if user is None:
        await message.answer("Пользователь с таким ID не найден")
        return

    elif user.banned:
        await message.answer(f"Пользователь {user.username} с таким ID уже забанен")

    await state.update_data(user_id=user.user_id)
    await message.answer("Введите сообщение бана для пользователя:\n Для выхода напишите <b>'отмена'.</b>")
    await state.set_state(CommandAction.waiting_for_reason)


@admin_main_router.message(CommandAction.waiting_for_reason, F.text)
async def cmd_reason_banned(
    message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Обрабатывает причину бана и блокирует пользователя"""
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Действия отменены", reply_markup=ADMIN_MAIN_KB)
        return

    if len(message.text) < 10:
        await message.answer("Слишком короткое сообщение, напиши ещё раз.")
        return

    data = await state.get_data()
    user_id = data['user_id']
    reason = message.text
    new_status = True

    # Add to bd
    await orm_ban_status_user(session, user_id, new_status)

    # end notify
    await bot.send_message(chat_id=user_id, text=reason)

    # Ban user
    await message.answer(
        f"<b>Пользователь ID: {user_id} забанен</b>\n"
                        f"<b>Причина: {reason}</b>", reply_markup=ADMIN_MAIN_KB)
    await state.clear()


@admin_main_router.message(Command("unban"))
async def cmd_send_user_unbanned(message: types.Message, state: FSMContext):
    """Запрашивает ID для разбана пользователя"""
    await message.answer("Введите ID пользователя, которого хотите разабанить\nДля выхода напишите: <b>'отмена'</b>")
    await state.set_state(CommandAction.waiting_for_unbaned)


@admin_main_router.message(CommandAction.waiting_for_unbaned)
async def cmd_unbanned(message: types.Message,state: FSMContext, session: AsyncSession):
    """Выполняет разблокировку пользователя"""
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("<b>Действия отменены</b>", reply_markup=ADMIN_MAIN_KB)
        return
    if not message.text.isdigit():
        await message.answer("Введите корректный числовой id")
        return
    user_id = int(message.text)
    user = await orm_select_user(session, user_id=user_id)
    if user is None:
        await message.answer("Пользователь с таким ID не найден")
        return
    elif user.banned is False:
        await state.clear()
        await message.answer("<b>Пользователь не был забанен</b>", reply_markup=ADMIN_MAIN_KB)
        return
    await message.answer(f"<b>Пользователь:</b> @{user.username} разбанен", reply_markup=ADMIN_MAIN_KB)
    new_status = False
    await orm_ban_status_user(session, user_id, new_status)
    state.clear()


@admin_main_router.message(Command("connect"))
async def cmd_connect_with_user(message: types.Message, state: FSMContext):
    """Запрашивает ID пользователя"""
    await message.answer("<b>Введите ID пользователя</b>, которому хотите отправить сообщение")
    await state.set_state(CommandAction.waiting_for_message)


@admin_main_router.message(CommandAction.waiting_for_message, F.text)
async def cmd_input_message(message: types.Message,
                            state: FSMContext, session: AsyncSession):
    """Обрабатывает ID"""
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Действия отменены", reply_markup=ADMIN_MAIN_KB)
        return

    if not message.text.isdigit():
        await message.answer("Введите корректный числовой ID")
        return
    user_id = int(message.text)
    user = await orm_select_user(session, user_id)

    if user is None:
        await message.answer("Пользователь с таки ID не найден")
        return

    await state.update_data(user_id=user.user_id)
    await message.answer("Введите сообщение для пользователя")
    await state.set_state(CommandAction.waiting_for_send_message)


@admin_main_router.message(CommandAction.waiting_for_send_message)
async def cmd_send_message_for_user(message: types.Message, state: FSMContext, bot: Bot):
    """Отправляет сообщение пользователю"""
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Действия отменены", reply_markup=ADMIN_MAIN_KB)
        return
    if len(message.text) < 3:
        await message.answer("<b>Слишком короткое сообщение</b>")
        return
    data = await state.get_data()
    user_id = data['user_id']
    message_for_user = message.text

    await bot.send_message(chat_id=user_id, text=message_for_user)
    await message.answer(f"<b>Сооббщение отправлено пользователю</b>\n<b>ID:</b> <code>{user_id}</code>\n<b>Текст сообщения:</b> {message_for_user}")
    await state.clear()

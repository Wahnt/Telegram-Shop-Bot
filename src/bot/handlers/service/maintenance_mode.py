from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.bot.filters.chat_types import ChatTypeFilter, IsAdmin


"""Роутер технического обслуживания бота, когда режим активен, мидлварь перехватывает все апдейты от пользователей
- Управление режимом"""

maintenance_router = Router()
maintenance_router.message.filter(IsAdmin())
maintenance_router.callback_query.filter(IsAdmin())


@maintenance_router.message(Command("maintenance"))
async def maintenance_control_panel(message: Message, state: FSMContext):
    """Выводит панель управления режимом"""
    current_state = await state.get_data()
    is_active = current_state.get("maintenance_mode", False)

    text = (
        "⚙️ <b>Управление режимом обслуживания</b>\n\n"
        f"Текущий статус: {'<b>🔴 АКТИВЕН</b>' if is_active else '<b>🟢 ВЫКЛЮЧЕН</b>'}\n\n"
        "Команды:\n"
        "/maintenance_on - Включить режим\n"
        "/maintenance_off - Выключить режим\n"
        "/maintenance_status - Проверить статус"
    )
    await message.answer(text)


@maintenance_router.message(Command("maintenance_on"))
async def maintenance_on(message: Message, state: FSMContext):
    await state.update_data(maintenance_mode=True)
    await message.answer(
        "🛠 <b>Режим технического обслуживания АКТИВИРОВАН</b>\n\n"
        "Все запросы пользователей будут получать уведомление о техработах."
    )


@maintenance_router.message(Command("maintenance_off"))
async def maintenance_off(message: Message, state: FSMContext):
    await state.update_data(maintenance_mode=False)
    await message.answer(
        "✅ <b>Режим технического обслуживания ОТКЛЮЧЕН</b>\n\n"
        "Бот снова доступен для всех пользователей."
    )


@maintenance_router.message(Command("maintenance_status"))
async def maintenance_status(message: Message, state: FSMContext):
    """Выводит текущий статус"""
    current_state = await state.get_data()
    is_active = current_state.get("maintenance_mode", False)

    status_text = (
        "🔴 <b>АКТИВЕН</b> - бот недоступен для пользователей"
        if is_active
        else "🟢 <b>ВЫКЛЮЧЕН</b> - бот работает в обычном режиме"
    )

    await message.answer(f"⚙️ <b>Статус технического обслуживания:</b>\n\n{status_text}")

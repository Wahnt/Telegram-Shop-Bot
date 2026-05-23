import re
from aiogram import Bot, types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from src.bot.filters.chat_types import ChatTypeFilter, IsAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.kbds.admin.inline_group_admin import AdminGroupCallback, get_admin_group_btns

""" Модуль административных команд в групповых чатах.

Содержит обработчик для:
- Получения ID чата (/get_id)
- Связи с пользователм через кнопку
- Управлениея статусами заказазов
- Удаление служебных сообщений

Доступно только администраторам в группах и супергруппах
"""

admin_group_router = Router()
admin_group_router.message.filter(
    ChatTypeFilter(["group", "supergroup"])), IsAdmin()


@admin_group_router.message(Command("get_id"))
async def cmd_get_chat_id(message: types.Message):
	""" ID текущего чата"""
	chat_id = message.chat.id
	await message.answer(f"<b>ID этого канала: {chat_id}</b>")

@admin_group_router.callback_query(AdminGroupCallback.filter(F.menu_name == "connect"))
async def cmd_connect_with_user(callback: types.CallbackQuery, bot: Bot):
	"""Создает кнпоку для перехода в чат с пользователем"""
	await callback.answer()

	match = re.search(r"🆔 ID: (\d+)", callback.message.text)

	user_id = int(match.group(1))

	await callback.message.answer(
		text=f"<b>⬇️ Перейти в чат с клиентом</b>",
		reply_markup=types.InlineKeyboardMarkup(
			inline_keyboard=[[
			types.InlineKeyboardButton(
				text="Открыть чат",
				url=f"tg://user?id={user_id}"),
			types.InlineKeyboardButton(
				text="Закрыть",
				callback_data="_delete_msg"
				)
			]]
			)

		)

@admin_group_router.callback_query(F.data.startswith("_delete_msg"))
async def cmd_delete_msg(callback: types.CallbackQuery):
	"""Удаляет сообщение с кнопками"""
	await callback.answer("")
	await callback.message.delete()


@admin_group_router.callback_query(AdminGroupCallback.filter(F.menu_name == "pinned"))
async def cmd_pinned_message(callback: types.CallbackQuery):
	"""Меняет статус заказа в сообщении (цикл из 3 состояний)"""
	_, purchase_id = callback.data.split(":")

	text = callback.message.text

	if "🟢 Заказ" in text:
		new_text = text.replace("🟢 Заказ", "🟡 Заказ (в работе)")
		new_status = "Заказ в работе"

	elif "🟡 Заказ (в работе)" in text:
		new_text = text.replace("🟡 Заказ (в работе)", "🔴 Заказ (завершен)")
		new_status = "Заказ завершен"

	else:
		new_text = text.replace("🔴 Заказ (завершен)", "🟢 Заказ")
		new_status = "Заказ открыт"

	await callback.message.edit_text(

		text=new_text,
		reply_markup=callback.message.reply_markup
		)
	await callback.answer(f"Статус заказа изменен на '{new_status}'",show_alert=True)

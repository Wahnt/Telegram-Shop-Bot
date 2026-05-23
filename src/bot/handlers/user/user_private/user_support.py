import asyncio
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters.callback_data import CallbackData
from aiogram import F, types, Router, Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.bot.filters.chat_types import ChatTypeFilter

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.models.models import  User, ChatSession

from src.core.database.orm_queries.support import (create_new_session_user, delete_session_user,
        get_active_chat_admin, get_waiting_session_and_update,get_id_support,get_admin_id_message,)

from src.bot.handlers.kbds.user.inline_catalog import MenuCallback, get_callback_btns
from src.bot.handlers.kbds.user.inline_support import (
    SupportCallback, get_user_btns, get_admin_btns,ask_to_support_btns,)

from src.bot.handlers.kbds.reply import get_keyboard
from src.bot.handlers.kbds.admin.inline_admin import get_admin_main_btn

from .support_task import handle_support_request
from src.core.cache.cache import cache 
from src.core.cache.cache import state_manager
from aiogram.fsm.storage.base import StorageKey

''' Роутер технической поддержки, здесь мы связываем внутри чата бота пользователя и администратора, условия работы роутера:
    На каждого пользователя, который отправил запрос есть только 1 администратор(1/1), при это администраторов может быть много,
    мы берём первого попавщегося с активным статусом.
    Администратор имеет статус для подключения, если он активный - то они будут дальше связаны в переписке внутри бота,
    если неактивный, переписки не бдует, будет только возможность создать запрос заново или отправить срочное сообщение,
    которое получит администратор, а дальше свяжется самостоятельно, либо внутри бота'''

user_support_router = Router()
user_support_router.message.filter(ChatTypeFilter(["private"]))

# Состояния для админа и пользователя
class ChatState(StatesGroup):
    
    waiting_for_support = State()
    in_chat_with_user = State()
    in_chat_with_admin = State()
    message_for_support = State()

@user_support_router.message(Command("support"))
async def cmd_support(message: types.Message):
    await message.answer(f"Хотите связаться с технической поддержкой?\nНажмите кнопку ниже.",reply_markup=get_user_btns())

@user_support_router.callback_query(SupportCallback.filter(F.menu_name == 'find_support'))
async def send_to_support_call(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    """Обрабатывает запрос пользователя"""
    user_id = callback.from_user.id
    first_name, username = callback.from_user.first_name, callback.from_user.username
    # Проверяем состояние пользователя 
    current_state = await state.get_state()
    if current_state and current_state != 'none':
        await callback.answer("У вас уже есть активный запрос", show_alert=True)
        return
    # Находим свободных администраторов с активным статусом, которые не в сессии, берем 1
    admin_id = await get_active_chat_admin(session)
    if not admin_id:
        await callback.answer()
        await bot.send_message(user_id,f"Сейчас все администраторы заняты, обратитесь, пожалуйста, позже или отправьте сообщение и мы сами с вами свяжимся.", reply_markup=ask_to_support_btns())
        return
    # Если такой есть и он не в сессии
    else:
        message_for_admin = await bot.send_message(admin_id,f"👤 Пользователь {first_name}\n<code>{user_id}</code>\nСоздал запрос в поддержку.\nСсылка: @{username}",reply_markup=get_admin_btns())
        await callback.answer()
        # Создаем запись в кэше 
        await cache.set(
            f"chat_session: {user_id}",
            {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "status": "waiting",
                "state": ""},
            ttl=120)
        # Создаем новую сессию чата и передаем туда id пользователя, меняем статус сессии на ожидание | waiting
        await create_new_session_user(session, user_id, username, first_name, 0)
        # Меняем состоние пользователя на ожидание 
        await state.set_state(ChatState.waiting_for_support)
        await state.update_data(admin_id=admin_id,user_id=user_id)
        res = await handle_support_request(bot,session, user_id)
        if res == True:
            await state.set_state(ChatState.in_chat_with_admin)
        else:
            await bot.delete_message(admin_id, message_id=message_for_admin.message_id)
            await delete_session_user(session,user_id)
            await state.clear()

@user_support_router.callback_query(SupportCallback.filter(F.menu_name == "send_message"))
async def change_message_to_support(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка срочного запроса в тех.поддержку"""
    await callback.answer()
    msg = await callback.message.edit_text(f"Будьте, пожалуйста, вежливы и опишите свою ситуацию в конкретной и понятной форме в 1 сообщение.")
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(ChatState.message_for_support)

@user_support_router.callback_query(SupportCallback.filter(F.menu_name == "close"))
async def close_message_to_support(callback: types.CallbackQuery,state: FSMContext):
    """Закрывает сообщение срочного запроса"""
    await state.clear()
    await callback.answer("")
    await callback.message.delete()
 
@user_support_router.message(ChatState.message_for_support)
async def send_message_to_support(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Отправляет сообщение пользователя администратору"""
    data = await state.get_data()
    msg_id = data.get("msg_id")
    await bot.delete_message(chat_id=message.from_user.id,message_id=msg_id)
    admin_id = await get_admin_id_message(session)
    await bot.send_message(admin_id,f"<b>Сообщение от пользователя</b>\n<b>Имя:</b>{message.from_user.first_name}\n<b>Ссылка:</b>(@{message.from_user.username})\n<b>ID:</b> <code>{message.from_user.id}</code>: \n\n"f"{message.text}")
    await message.answer("Ваше сообщение отправлено администратору, в ближайшее время с вами свяжутся.",reply_markup=get_callback_btns(btns={"Вернуться в магазин ⬅️" : "shop"}))
    await state.clear()

@user_support_router.callback_query(SupportCallback.filter(F.menu_name == "answer_end"))
async def end_waiting_user(callback: types.CallbackQuery, session: AsyncSession,state: FSMContext):
    """Обрабатывает отмену запроса"""
    await callback.answer("Вы отменили запрос")
    await state.clear()
    await callback.message.delete()

@user_support_router.callback_query(SupportCallback.filter(F.menu_name == "answer_to_user"))
async def answer_support_call(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    """Обрабатывает принятие запроса админом, соединяет пользователя и администратора в переписку"""
    admin_id = callback.from_user.id
    # Получаем сессию чата и обновляем данные пользователя и администратора
    chat_session= await get_waiting_session_and_update(session, admin_id)
    # Добавляем админа в кэш
    await cache.set(
        f"chat_session:{chat_session.user_id}",
        {
        "user_id": chat_session.user_id,
        "admin_id":admin_id,
        "status":"active"},
    ttl=120)
    await asyncio.sleep(2)
    # Уведомляем пользователя
    await bot.send_message(chat_session.user_id,
            f"🎟️ Администратор подключился к чату.\nМожете задавать вопросы.\nБудьте, пожалуйста, вежливы.")
    # Уведомляем администратора
    await callback.message.edit_text(
            f"💬 Вы в чате с пользователем: {chat_session.first_name}\n"
            "Отправляйте сообщения, а я их буду пересылать пользователю.\nДля завершения чата напишите: ' . '")
    # Устанавливаем состояние для администратора
    await state.set_state(ChatState.in_chat_with_user)
    await callback.answer()

@user_support_router.message(ChatState.in_chat_with_admin,F.content_type == "text")
async def handle_user_message(message: types.Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Отправялет сообщения пользователя администратору"""
    user_id = message.from_user.id
    admin_id = await get_id_support(session,user_id)
    await bot.send_message(admin_id, f"👤 {message.from_user.first_name}:\n{message.text}")

@user_support_router.message(ChatState.in_chat_with_user,F.text.lower() == ".")
async def handler_admin_exit(message: types.Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Обрабатывает завершение ччата администратором"""
    admin_id = message.from_user.id
    user_id = await get_id_support(session, admin_id, True)
    await bot.send_message(chat_id=int(user_id),text=f"Администратор завершил чат, благодарим вас за активность.",
                            reply_markup=get_callback_btns(btns={"Вернуться в магазин ⬅️" : "shop"}))
    # Удаляем сессию и меняем статус администратора
    await delete_session_user(session, user_id, admin_id)
    # Очищаем состояние администратора
    await state.clear()
    # Очищаем состояние пользователя
    await state_manager.reset_user_state(bot, user_id)
    await message.answer(f"Вы завершили чат", reply_markup=get_admin_main_btn())

@user_support_router.message(ChatState.in_chat_with_user,F.content_type == "text")
async def handle_admin_message(message: types.Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Отправляет сообщения администратора пользвоателю"""
    admin_id = message.from_user.id
    user_id = await get_id_support(session, admin_id, is_admin=True)
    await bot.send_message(user_id,f"{message.text}")
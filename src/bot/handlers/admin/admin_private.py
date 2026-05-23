from datetime import datetime
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.types.callback_query import CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.orm_queries.admin import (
    orm_change_status_admin,
    orm_get_status_admin,
)
from src.core.database.orm_queries.stat import (
    get_total_users,
    get_new_users,
    get_active_users,
    get_conversion_rate,
    get_revenue_stats,
    get_top_products,
    get_promo_stats,)

from src.core.database.orm_queries.support import get_id_support
from src.core.database.orm_queries.broadcast import get_all_active_users, update_users_status
from src.core.database.orm_queries.commerce import get_user_with_relations
from src.core.database.models.models import User, Payment

from src.bot.filters.chat_types import ChatTypeFilter, IsAdmin

from src.bot.handlers.kbds.admin.inline_admin import AdminCallback, get_admin_menu_btns, get_admin_main_btn, get_admin_user_action_btn, get_admin_sendler_action_btns

from ..admin.sendler import start_broadcast

'''  Роутер для администратора.
- Поменять статус администратора для тех.поддержки
- Создать рассылку
- Посмотреть статистику
- Найти пользователя'''

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_MENU_KB = get_admin_menu_btns()  # Main Menu
ADMIN_MAIN_KB = get_admin_main_btn()  # Get back to main menu // 1 btn
ADMIN_USERS_KB = get_admin_user_action_btn()  # Action with user
ADMIN_SENDLER_KB = get_admin_sendler_action_btns()  # Sendler // Broadcast

# Действия с пользователем
class ActionWithUserStates(StatesGroup):
    waiting_for_request = State()
    waiting_for_message = State()
    waiting_for_ban = State()

# Рассылка
class BroadcastStates(StatesGroup):
    waiting_for_text = State()


# Флаги/Статусы администратора для тех.поддержки
status_messages = {
    0: "🔴\n→ <strong>Не активный</strong>\nВы отключены от службы поддержки.",
    1: "🟢\n→ <strong>Активный</strong>\nВы подключены к службе поддержки.",
    2: "🟡\n→ <strong>В сессии с пользователем.</strong>\nБот автоматически поменяет ваш статус после завершения чата.",
}


@admin_router.message(or_f(Command("admin"), (F.text.lower() == "админ")))
async def cmd_admin(message: types.Message):
    user = message.from_user
    await message.answer(f"<b>Добро пожаловать</b> в Панель администратора\n{user.first_name}", reply_markup=ADMIN_MAIN_KB)


@admin_router.callback_query(AdminCallback.filter(F.menu_name == "main"))
async def get_admin_main_menu(callback: types.CallbackQuery, session: AsyncSession):
    """Главное меню панели администратора"""
    await callback.answer()
    admin = callback.from_user

    status = await orm_get_status_admin(session, admin.id)
    response = format_admin_main_menu_response(admin, status)
    if status == 2:
        await handle_support_admin_flow(session, callback, admin)
        await callback.message.answer(text=response)

    else:
        await callback.message.edit_text(
            text=response, reply_markup=ADMIN_MENU_KB)


async def handle_support_admin_flow(
        session: AsyncSession, callback: types.CallbackQuery, admin: types.User):
    """Вывод данных пользователя, если администратора находится в чат-сессии тех. поддержки"""
    user_id = await get_id_support(session, admin.id, is_admin=True)
    user = await get_user_with_relations(session, user_id)

    user_info = [

        f"<b>Пользователь</b>",
        f"🆔: <code>{user.user_id}</code>",
        f"👤 Username: @{user.username or 'не указан'}",
        f"👤 Имя: {user.first_name or 'не указано'}"
    ]

    if user.payments:
        user_info.append("\n💳 <b>Успешные платежи:</b>")
        user_info.extend(format_payment_info(payment)
                         for payment in user.payments)
    await callback.message.answer("\n".join(user_info))


def format_payment_info(payment: Payment) -> str:
    payment_lines = [
        f"\n💰 <b>Платеж:</b> {payment.id}",
        f"📅 Дата: {payment.created.strftime('%Y-%m-%d %H:%M')}",
        f"💵 Сумма: {payment.amount} {payment.currency}",
        f"🔢 Номер платежа: <code>{payment.provider_payment_id}</code>"
    ]

    if payment.purchases:
        purchase = payment.purchases
        payment_lines.append(f"\n🛒 <i>Покупка:</i> {purchase.id}")

        if purchase.purchases_items:
            payment_lines.append("<i>Продукты:</i>")
            payment_lines.extend(
                f" • {item.product.name} × {item.quantity} ({item.final_price} {payment.currency})"
                for item in purchase.purchases_items
            )

    return "\n".join(payment_lines)


def format_admin_main_menu_response(admin: types.User, status: int) -> str:
    """Форматирует главное меню администратора"""
    return (
        "<strong>Панель администратора</strong>\n"
        f"<b>Данные сессии:</b>\n"
        f"<b>Username:</b> @{admin.username}\n"
        f"<b>ID:</b> {admin.id}\n"
        f"<i>Статус:</i> {status_messages.get(status, 'Неизвестен')}"
    )


@admin_router.callback_query(AdminCallback.filter(F.menu_name == 'support'))
async def change_admin_status(callback: types.CallbackQuery, callback_data: AdminCallback, session: AsyncSession):
    """Переключает статус на противоположный"""
    await callback.answer()
    user = callback.from_user
    current_status = await orm_get_status_admin(session, user.id)
    await orm_change_status_admin(session, user.id, 1 if current_status == 0 else 0)
    response = (
        "<strong>Панель администратора</strong>\n"
        f"<b>Данные сессии</b>:\n"
        f"<b>Username</b>: @{user.username}\n"
        f"<b>ID</b>: {user.id}\n"
        f"<i>Статус</i>: {status_messages.get(0) if current_status == 1 else status_messages.get(1) if current_status == 0 else status_messages.get(2)}"
    )

    await callback.message.edit_text(response, reply_markup=ADMIN_MENU_KB if current_status != 2 else None)


@admin_router.callback_query(AdminCallback.filter(F.menu_name == "users"))
async def cmd_users(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик действий с пользователями"""
    await callback.answer()
    response = """<b>ℹ️ info</b>\nВведите ID или <strong>username</strong> пользователя.\nДля выхода напишите <b>'отмена'.</b>
                 """
    await callback.message.edit_text(response)
    await state.set_state(ActionWithUserStates.waiting_for_request)


@admin_router.message(ActionWithUserStates.waiting_for_request,
                      F.text.lower() != "отмена")
async def cmd_search_user(message: types.Message,
                          session: AsyncSession, state: FSMContext):
    """Обрабокта выхода"""
    search_query = message.text.strip()
    user = None

    # ID search
    if search_query.isdigit():
        user = await get_user_with_relations(session, user_id=int(search_query))

    # Username search
    elif isinstance(search_query, str):
        username = search_query[1:] if search_query.startswith(
            "@") else search_query
        user = await get_user_with_relations(session, username=username)
    else:
        await message.answer("Некорректный формат запроса!")
        return

    if user is None:
        await message.answer("Пользователь не найден")
        return

    response = [
        f"<b>Пользователь</b>\n",
        f"🆔: <code>{user.user_id}</code>",
        f"Username: @{user.username if user.username else 'не указан'}",
        f"Имя: {user.first_name if user.first_name else 'не указано'}\n"
    ]
    if user.payments:
        response.append("💳<b> Успешные платежи</b>")
        for payment in user.payments:
            payment_info = [
                f"\n<b>💰 Платеж:</b> {payment.id}\n<b>Дата: </b>{payment.created.strftime('%Y-%m-%d %H:%M')}\
                \n<b>Сумма:</b> {payment.amount}  {payment.currency}\
                \n<b>Номер платежа(yookassa): </b> <code>{payment.provider_payment_id}</code>"]

            if payment.purchases:
                purchase = payment.purchases
                purchase_info = [

                    f"\n<i>Покупка:</i> {purchase.id}"

                ]

                if purchase.purchases_items:
                    purchase_info.append("<i>Продукты:</i>")
                    for item in purchase.purchases_items:
                        purchase_info.append(

                            f" • {item.product.name} × {item.quantity}"
                            f" • {item.final_price} {payment.currency}"

                        )
                payment_info.append("\n".join(purchase_info))

            response.append("\n".join(payment_info))

    await message.answer(text="\n".join(response), reply_markup=ADMIN_MAIN_KB)
    await state.clear()


@admin_router.message(ActionWithUserStates.waiting_for_request,
                      F.text.lower() == "отмена")
async def cmd_cancel_broadcast(message: types.Message, state: FSMContext):
    await message.answer("<b>Действия отменены</b>", reply_markup=ADMIN_MAIN_KB)
    await state.clear()


@admin_router.callback_query(AdminCallback.filter(F.menu_name == "statistics"))
async def cmd_statistic(callback: types.CallbackQuery, session: AsyncSession):
    """Выводит статистику"""
    await callback.answer()
    users = await get_total_users(session)
    day = await get_new_users(session, "day")
    week = await get_new_users(session, "week")
    active_users = await get_active_users(session)
    conversion_rate = await get_conversion_rate(session)
    revenue_stats = await get_revenue_stats(session)
    top_products = await get_top_products(session)
    promo_stats = await get_promo_stats(session)

    response = (
        f"<b>📊 Статистика пользователей на {datetime.now().strftime('%d.%m.%Y')}</b>\n\n"

        f"<b>👥 Пользователи:</b>\n"
        f"•  Всего: {users}\n"
        f"•  Новых за день: {day}\n"
        f"•  Новых за неделю: {week}\n"
        f"•  Активных (30 дн.): {active_users}\n"
        f"•  Конверсия в покупку: {conversion_rate}\n"
        f"•  Retention: \n\n"

        f"<b>💵 Продажи:</b>\n"
        f"•  Текущий месяц: {revenue_stats['month']}₽\n"
        f"•  Средний чек: {revenue_stats['avg']}₽\n\n"

        f"<b>🎫 Промокоды:</b>\n"
        f"•  Общее количество использований: {promo_stats['total_used']}\n"
        f"•  Самый популярный: {promo_stats['top_promo']}\n\n"
        f"<b>🏆 Топ продуктов:</b>\n"


    )

    for i, product in enumerate(top_products, 1):
        response += (
            f"<b>{i}. {product['name']}\n</b>"
            f"<b>• Количество продаж: {product['sales']}</b>\n"
            f"<b>• Выручка: {float(product['revenue']):.2f} ₽</b>\n"

        )

    await callback.message.edit_text(response, reply_markup=ADMIN_MAIN_KB)


@admin_router.callback_query(AdminCallback.filter(F.menu_name == "sendler"))
async def cmd_sendler(callback: types.CallbackQuery):
    """Выводит инфо для рассылки"""
    await callback.answer()
    response = (
        f"<b>ℹ️ info</b>\n"
        f"Рассылка осуществляется всем пользователям, которые подписаны на бота.\n"
        f"Подготовьте заранее отредактированный текст и приступайте.\n"
    )
    await callback.message.edit_text(response, reply_markup=ADMIN_SENDLER_KB)


@admin_router.callback_query(StateFilter(None),
                             AdminCallback.filter(F.menu_name == "start_broadcast_"))
async def cmd_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает текст для рассылки"""
    await callback.message.delete()
    await callback.message.answer(
        "<b>Введите текст для рассылки</b>\nДля выхода напишите <b>'отмена'</b>", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(BroadcastStates.waiting_for_text)


@admin_router.message(BroadcastStates.waiting_for_text,F.text.lower() != "отмена")
async def cmd_start_broadcast(
        message: types.Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Реализует рассылку пользователям"""
    # Получаем всех пользователей с активным статусом
    user_ids = await get_all_active_users(session)
    if not user_ids:
        await message.answer("<b>Нет активных пользователей для рассылки.</b>")
        await state.clear()
        return

    broadcast_text = message.text

    if not broadcast_text:
        return await message.answer("<b>Введите текст рассылки</b>")

    result = await start_broadcast(bot, session, user_ids, broadcast_text[:4096])

    # Обновляем статусы пользователей
    await update_users_status(session, success_ids=result.get('success_ids', []),
                              blocked_ids=result.get('blocked_ids', []))

    report = (

        "<strong>Отчет о рассылке:</strong>\n"
        f"✅ Успешно: {len(result.get('success_ids', []))}\n"
        f"❌ Ошибка: {result.get('failed', 0)}\n"
        f"🚫 Заблокировали бота: {len(result.get('blocked_ids', []))}"
    )
    await message.answer(report, reply_markup=ADMIN_MAIN_KB)

    await state.clear()
    
@admin_router.message(BroadcastStates.waiting_for_text,
                      F.text.lower() == "отмена")
async def cmd_cancel_broadcast(message: types.Message, state: FSMContext):
    await message.answer("Рассылка отменена", reply_markup=ADMIN_MAIN_KB)
    await state.clear()

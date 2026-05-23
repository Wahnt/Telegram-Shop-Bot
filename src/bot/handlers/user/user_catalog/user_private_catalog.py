import os
import asyncio
from datetime import datetime
from decimal import Decimal
from aiogram import F, types, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters import Command, StateFilter

from aiogram.types import PreCheckoutQuery
from aiogram.types.labeled_price import LabeledPrice

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.orm_queries.catalog import (
    orm_add_to_cart,
    orm_get_user_carts,
    orm_delete_user_carts,
)  # , orm_get_user_cart_with_categories
from src.core.database.orm_queries.commerce import create_payment_with_purchase
from src.core.database.orm_queries.loyalty import orm_send_promocode, orm_get_user_promocode
from src.core.database.orm_queries.commerce import get_user_purchases

from src.bot.filters.chat_types import ChatTypeFilter

from src.bot.handlers.kbds.admin.inline_group_admin import AdminGroupCallback, get_admin_group_btns
from src.bot.handlers.kbds.user.inline_catalog import MenuCallback, get_callback_btns, get_user_catalog_btns
from src.bot.handlers.kbds.reply import get_keyboard

from src.bot.handlers.user.user_catalog.private_catalog_process import get_menu

"""Модуль главного пользовательского меню магазина
- Просмотр каталога
- Добавление продукта в корзину
- Просмотр своих Покупок
- Ввод промокода
- Просмотр корзины
- Просмотр отзывов
- Просмотр бесплатного контента
- Оплата"""

user_private_catalog_router = Router()
user_private_catalog_router.message.filter(ChatTypeFilter(["private"]))


PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")
CURRENCY = "RUB"
EVENT_CHAT = os.getenv("EVENT_CHAT")

KB_EXIT = get_keyboard()

KB_GROUP = get_admin_group_btns()

ADMIN_MAIN = os.getenv("ADMIN_MAIN")


class SendPromocode(StatesGroup):
    waiting_for_promo = State()


@user_private_catalog_router.callback_query(F.data.startswith("shop"))
async def catalog_cmd(callback: types.CallbackQuery,
                      session: AsyncSession, bot: Bot):
    """Выводит главное пользовательское меню"""
    await callback.answer()
    await callback.message.delete()
    media, reply_markup = await get_menu(session, level=0, menu_name="main")
    await bot.send_photo(
        callback.from_user.id,
        media.media,
        caption=media.caption,
        reply_markup=reply_markup,
    )


async def add_to_cart(
    callback: types.CallbackQuery, callback_data: MenuCallback, session: AsyncSession
):
    """Добавялет продукт в корзину"""
    user = callback.from_user
    await orm_add_to_cart(session, user_id=user.id, product_id=callback_data.product_id)
    await callback.answer("Продукт добавлен в корзину.")


@user_private_catalog_router.callback_query(MenuCallback.filter())
async def user_menu(
    callback: types.CallbackQuery,
    callback_data: MenuCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
):
    """Возвращает объект навигации"""
    # Добавление продукта в корзину
    if callback_data.menu_name == "add_to_cart":
        await add_to_cart(callback, callback_data, session)
        return
    # Выход на оплату из корзины - кнопка 'Оформить
    if callback_data.menu_name == "order":
        await callback.answer()
        user_id = int(callback.from_user.id)
        # Удаляем сообщение с каталогом, чтобы сохранить состояние корзины
        await callback.message.delete()
        await user_payment(session, bot, user_id)
        return

    # Оставить отзыв
    if callback_data.menu_name == "feedback":
        await callback.answer()
        user_id = int(callback.from_user.id)
        await callback.message.delete()
        purchases = await get_user_purchases(session, callback.from_user.id)

        if not purchases:
            await callback.message.answer(
                f"<b>Отзыв можно оставить после прохождения сессии или курса.</b>",
                reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
            )
            return
        # Открыть покупки
        else:
            await callback.message.answer(
                f"Раздел в разработке",
                reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
            )
            return

    # Выход на канал с бесплатным контентом
    if callback_data.menu_name == "free":
        await callback.answer()
        user_id = callback.from_user.id
        await callback.message.delete()
        await callback.message.answer(
            f"Раздел в разработке",
            reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
        )
        return

    # Ассист Движение
    if callback_data.menu_name == "assist":
        await callback.answer()
        user_id = callback.from_user.id
        await callback.message.delete()
        await callback.message.answer(
            f"",
            reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
        )
        return

    # Промокоды
    if callback_data.menu_name == "promocode":
        await callback.answer()
        await callback.message.delete()

        actual_promo = await orm_get_user_promocode(session, callback.from_user.id)
        if actual_promo:
            # Сообщение о состоянии промокода
            response = f""" • <b>Ваш промокод:</b> <code>{actual_promo.code}</code>\
						\n • {actual_promo.description}\
						\n • {"<b>Скидка будет применена при оформлении покупки</b>" if actual_promo.is_active == True else "<b>Промокод неактивен, введите, пожалуйста, новый.</b>"}\
						\n • <b>Количество применений для всех пользователей</b> - <i>{actual_promo.usage}</i>"""
            await callback.message.answer(
                response,
                reply_markup=get_callback_btns(
                    btns={"Назад ⬅️": "shop", "Поменять 🔄": "send_promo"}
                ),
            )
            return
        if actual_promo is None:
            await callback.message.answer(
                f"<b>Введите ваш промокод: 🎫</b>",
                reply_markup=get_keyboard("Выйти", sizes=(1,)),
            )
            await state.set_state(SendPromocode.waiting_for_promo)
            return

    # Посмотреть покупки пользователя, если был применен промкод, будет
    # привязан к конкретной покупке
    if callback_data.menu_name == "purchases":
        await callback.answer()
        await callback.message.delete()
        purchases = await get_user_purchases(session, callback.from_user.id)

        if not purchases:
            await callback.message.answer(
                f"<b>У вас пока нет покупок</b>",
                reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
            )
            return
        # Формируем ответ
        response = ["🛒 <b>История моих покупок:</b>\n"]
        # Добавляем покупку
        for purchase in purchases:
            response.append(
                f"\n<b>Дата оформления:</b> {purchase.created.strftime('%d.%m.%Y')}\n<b>📦 ID Заказа:</b> {purchase.id}")
            # Добавляем промокод
            if purchase.promocode and purchase.promocode.discount_type == "individual":
                response.append(
                    f"🎫 <b>Промокод:</b> {purchase.promocode.code}\n"
                    f"🔖 <b>info:</b> {purchase.promocode.description}\n"
                )
            # Добавляем связанные продукты с покупкой
            for item in purchase.purchases_items:
                response.append(
                    f"  ├ <b>{item.product_name}</b>\n"
                    f"  ├ Количество: {item.quantity}\n"
                    f"  ├ Цена: {item.product_price} ₽\n"
                    f"  └ <i>Итог: {item.final_price * item.quantity} ₽</i>\n"
                )
            # Итоговая стоимость
            total = sum(
                item.final_price * item.quantity for item in purchase.purchases_items
            )

            response.append(f"\n💳 <i>Общая сумма:</i> {total} ₽\n")

        await callback.message.answer(
            "\n".join(response),
            reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
        )
        return

    media, reply_markup = await get_menu(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id,
    )
    await callback.message.edit_media(media=media, reply_markup=reply_markup)
    await callback.answer()


async def user_payment(session: AsyncSession, bot: Bot, user_id: int):
    """Принимает продукты из корзины пользователя и возвращает инвойс для оплаты"""
    # Получаем промокод пользователя
    promocode = await orm_get_user_promocode(session, user_id)
    # Получаем корзину пользователя
    carts = await orm_get_user_carts(session, user_id)
    total_price = 0
    text = []
    discount_applied = False

    # Добавляем список продуктов и финальную стоимость с учетом скидки
    for cart in carts:
        original_price = cart.product.price * cart.quantity
        final_price = original_price
        # Применяем скидку в зависимости какой промокод и какая категория
        # продукта
        if promocode and promocode.is_active:
            if (
                promocode.discount_type == "individual"
                and cart.product.category_id == 1
            ) or (promocode.discount_type == "group" and cart.product.category_id == 2):
                discount = int(promocode.discount_value)
                final_price = original_price * (100 - discount) / 100
                discount_price = original_price - final_price
                discount_applied = True
                text.append(
                    f"\n • {cart.product.name}"
                    f"\n   {cart.quantity}шт - {original_price}₽"
                    f"\n   🎫 Скидка {discount}%: {discount_price}₽\n"
                )
            else:
                text.append(
                    f"\n • {cart.product.name}"
                    f"\n   {cart.quantity}шт - {original_price}₽"
                )
        else:
            text.append(
                f"\n • {cart.product.name}"
                f"\n   {cart.quantity}шт - {original_price}₽"
            )

        total_price += int(final_price)

    # Финальное описание
    description = "".join(text) + f"\n\n💳 Итоговая сумма: {total_price}₽"

    # Добавляем промокод к покупке
    if discount_applied:
        description += f"\n\n🎫 Покупка по промокоду\n {promocode.code}"

    # Отправляем инвойс пользователю + кнопка для возвращения на главное меню
    prices = [LabeledPrice(label="Оплатить", amount=total_price * 100)]
    await bot.send_message(
        chat_id=user_id,
        text=f"<b>⬅️ Вернуться на главное меню</b>",
        reply_markup=get_callback_btns(btns={"Назад": "shop"}),
    )
    await bot.send_invoice(
        chat_id=user_id,
        title=f"🛍️ Оплата заказа",
        description=description,
        payload=f"{user_id}",  # str
        provider_token=PROVIDER_TOKEN,
        currency=CURRENCY,
        start_parameter="payment",
        prices=prices,
    )


@user_private_catalog_router.pre_checkout_query()
async def process_pre_checkout_query(
        pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Внтуренний метод телеграм для отлова успешной оплаты"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def create_one_time_invite(bot: Bot, chat_id: str) -> str:
    """Создает одноразовую ссылку на закрытый канал для пользователя
    - Для групповых категорий продуктов"""
    invite = await bot.create_chat_invite_link(
        chat_id=chat_id, name="One-time access", member_limit=1
    )

    return invite.invite_link


@user_private_catalog_router.message(F.successful_payment)
async def process_successful_payment(
    message: types.Message, session: AsyncSession, bot: Bot
):
    """Обрабатывает успешную оплату и действия после"""
    payment = message.successful_payment
    user_id = message.from_user.id
    # Получаем промокод пользователя
    promocode = await orm_get_user_promocode(session, user_id)
    # Получаем корзину пользователя
    carts = await orm_get_user_carts(session, user_id)
    # Платежные данные
    payment_data = {
        "amount": Decimal(payment.total_amount) / 100,
        "currency": payment.currency,
        "telegram_payment_id": payment.telegram_payment_charge_id,
        "provider_payment_id": payment.provider_payment_charge_id,
    }

    payment, purchase = await create_payment_with_purchase(
        session=session,
        user_id=user_id,
        payment_data=payment_data,
        carts=carts,
        promocode=promocode,
    )

    # Создаем список продуктов по категориям
    individual_products = []
    group_products = []
    group_links = []

    for item in carts:
        if item.product.category_id == 1:
            individual_products.append(
                f"• {item.product.name} (количество: {item.quantity})"
            )
        if item.product.category_id == 2:
            invite_link = await create_one_time_invite(bot, item.product.link)
            group_products.append(
                f"🔗 {item.product.name}: (количество: {item.quantity})"
            )
            group_links.append(
                f"• {item.product.name}: {invite_link}\n"
                f"❗ Ссылка одноразовая, только для 1 пользователя\n"
            )

    # Если был куплен индивидуальный продукт(в связке с другим или нет -
    # неважно), отправялем сообщение в чат к коучу
    coach_message = (
        f"<b>🟢 Заказ</b> 🆔: <code>{purchase.id}</code>\n"
        f"<b>Дата</b> <i>{datetime.now().strftime('%d.%m.%Y')}</i>\n\n"
        f"👤 Пользователь: @{message.from_user.username or 'нет username'}\n"
        f"🆔 ID: {user_id}\n"
        f"📝 Имя: {message.from_user.first_name}\n\n"
        f"🛒 <b>Список продуктов:</b>\n"
        f"{chr(10).join(individual_products)}\n\n"
        f"{chr(10).join(group_products) if group_products else 'Групповых продуктов нет'}\n\n"
        f"💰 Общая Сумма: {payment.amount} {payment.currency}\n"
    )

    # Ответ для пользователя
    acces_message = [
        "🎉 <b>Благодарим вас за покупку</b>!\
			\n✅️ Оплата прошла успешно.",
        "\n\n<b>Доступ к продуктам:</b>",
    ]

    # Добавляем индивидуальные продукты
    if individual_products:
        acces_message.append(
            "\n\nС вами свяжется <b>Администратор / Наставник</b> в ближайшее время для назначение даты встречи,\
				 			если если у вас "
        )

        await bot.send_message(
            chat_id=EVENT_CHAT, text=coach_message, reply_markup=KB_GROUP
        )

        if promocode and promocode.discount_type == "individual":
            acces_message += f"\n\n🎫 Промокод\n{promocode.code}"

    # Добавляем групповые продукты
    if group_products:
        acces_message.append(f"\n\n<b>⬇️ Ссылки для входа</b>")
        acces_message.extend([f"\n{link}" for link in group_links])

        if promocode and promocode.discount_type == "group":
            acces_message += f"\n\n🎫 Промокод\n{promocode.code}"

    await bot.send_message(
        chat_id=user_id,
        text="".join(acces_message),
        disable_web_page_preview=True,
        reply_markup=get_callback_btns(btns={"Назад ⬅️": "shop"}),
    )

    # Очищаем корзину пользователя
    await orm_delete_user_carts(session, user_id)


# Посмотреть активные промокоды
@user_private_catalog_router.callback_query(F.data == "send_promo")
async def hnadle_send_promocode(
        callback: types.CallbackQuery, state: FSMContext):
    """Ожидает ввод промокода, Возвращает FSM -> waiting_for_promo"""
    await callback.answer()
    await callback.message.answer(
        f"<b>Введите ваш промокод: 🎫</b>",
        reply_markup=get_keyboard("Выйти", sizes=(1,)),
    )
    await state.set_state(SendPromocode.waiting_for_promo)


@user_private_catalog_router.message(
    StateFilter(SendPromocode.waiting_for_promo))
async def send_promocode(
    message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot
):
    """Обработчки промокода пользователя"""
    user_input = message.text.strip().upper()

    if message.text == "Выйти":
        sent_message = await message.answer(
            f"<b>Действия отменены</b>", reply_markup=types.ReplyKeyboardRemove()
        )
        await asyncio.sleep(2)
        await bot.delete_message(
            chat_id=message.from_user.id, message_id=sent_message.message_id
        )
        media, reply_markup = await get_menu(session, level=0, menu_name="main")
        await bot.send_photo(
            message.from_user.id,
            media.media,
            caption=media.caption,
            reply_markup=reply_markup,
        )
        await state.clear()
        return
    promo = await orm_send_promocode(session, user_input, message.from_user.id)

    if promo is None:
        await message.answer(
            "<b>Промокод недействителен❗</b>",
            reply_markup=get_keyboard("Выйти", sizes=(1,)),
        )
        return

        # Логика на будущее
    elif promo.discount_type == "exclusive":
        # Exclusive content
        await message.answer(
            f"<b>Поздравляю, теперь у вас есть доступ к эксклюзивному контенту!✅</b>"
        )
        return

    elif promo.discount_type == "gift":
        # Подарочный промокод
        await message.answer(
            f"<b>Промокод успешно применен.✅</b>\
							\nВам доступна 1 трансформационная сессия, с вами свяжутся в ближайшее время."
        )
        await bot.send_message(
            chat_id=EVENT_CHAT,
            text=f"<b>Пользователь</b> @{message.from_user.username}\
														\n<b>Имя</b> {message.from_user.first_name}\
														\n<b>Продукты</b> Промокод на 1 бесплатную сессию.\
														\n<b>Статус</b> 🔴 В процессе выполения.",
            reply_markup=KB_GROUP,
        )
        media, reply_markup = await get_menu(session, level=0, menu_name="main")
        await bot.send_photo(
            message.from_user.id,
            media.media,
            caption=media.caption,
            reply_markup=reply_markup,
        )
        await state.clear()
    else:
        await message.answer(
            f"<b>Промокод успешно применен.✅</b>\
							\nТеперь у вас есть:\
							\n{promo.description}",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await bot.delete_message(
            chat_id=message.from_user.id, message_id=message.message_id
        )
        await asyncio.sleep(3)
        media, reply_markup = await get_menu(session, level=0, menu_name="main")
        await bot.send_photo(
            message.from_user.id,
            media.media,
            caption=media.caption,
            reply_markup=reply_markup,
        )
        await state.clear()
        return


@user_private_catalog_router.message(SendPromocode.waiting_for_promo)
async def send_promocode_check(message: types.Message, state: FSMContext):
    """Отлов некорректных значений"""
    await message.answer(f"<b>Введите корректное значение.</b>")

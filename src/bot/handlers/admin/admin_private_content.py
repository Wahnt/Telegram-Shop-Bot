import os
import asyncio
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.types.callback_query import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.orm_queries.catalog import (
    orm_add_product,
    orm_delete_product,
    orm_get_product,
    orm_get_products_admin,
    orm_update_product,
    orm_recove_product,
    orm_remove_product,
    orm_get_categories,
    orm_get_info_pages,
    orm_change_banner_image,
    orm_delete_from_cart_all_users,
)

from src.core.database.orm_queries.loyalty import (
    orm_get_all_promocodes,
    orm_deactivate_promocode,
    orm_add_promocode,
)

from src.bot.filters.chat_types import ChatTypeFilter, IsAdmin

from src.bot.handlers.kbds.inline import get_callback_btns
from src.bot.handlers.kbds.admin.inline_admin import (
    AdminCallback,
    get_admin_main_btn,
    get_admin_promo_action_btn,
)
from src.core.config.settings import app_settings

"""Административный роутер по работе с контентом
- Добавление/Удаление/Изменение Продукта/Баннера/Промокода"""

ADMIN_MAIN_KB = get_admin_main_btn()

EVENT_CHAT = app_settings.EVENT_CHAT

admin_content_router = Router()
admin_content_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


class AddBanner(StatesGroup):
    image = State()


class AddProduct(StatesGroup):
    name = State()
    description = State()
    category = State()
    link = State()
    price = State()
    image = State()

    product_for_change = None

    texts = {
        "AddProduct:name": "Введите название заново:",
        "AddProduct:description": "Введите описание заново 📃:",
        "AddProduct.category": "Выберете категорию заново 🏷️:",
        "AddProduct.link": "Введите ID чата заново 🔗:",
        "AddProduct:price": "Введите стоимость заново 💵:",
        "AddProduct:image": "Это был последний шаг",
    }


class AddPromocode(StatesGroup):

    name = State()
    description = State()
    discount_type = State()
    discount_value = State()
    usage = State()


type_list = ("individual", "group", "exclusive", "gift")


@admin_content_router.callback_query(
    StateFilter(None), AdminCallback.filter(F.menu_name == "banner")
)
async def add_image_banner_two(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    """Добавялет баннер"""
    await callback.answer()
    pages_name = [page.name for page in await orm_get_info_pages(session)]
    message = await callback.message.edit_text(
        f"Отправьте фото баннера.\nДля выхода напишите <b>'отмена'</b>\nВ описании укажите для какой страницы - main, catalog, cart"
    )
    await state.update_data(message_id=message.message_id)
    await state.set_state(AddBanner.image)


@admin_content_router.message(AddBanner.image, F.text | (F.photo & F.caption))
async def add_banner(
    message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot
):
    """Изменяет баннер"""
    if message.text == "отмена" and not message.photo:
        data = await state.get_data()
        await message.delete()
        if "message_id" in data:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=data["message_id"]
            )
        await message.answer("<b>Действия отменены</b>", reply_markup=ADMIN_MAIN_KB)
        await state.clear()
        return
    if not message.caption:
        await message.answer("Укажите название страницы в подписи к фото🖼️")
        return

    image_id = message.photo[-1].file_id
    for_page = message.caption.strip()
    pages_name = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in pages_name:
        await message.answer(
            f"Введите корректное название страницы,<b>например:</b> main, catalog, cart"
        )
        return
    await orm_change_banner_image(session, for_page, image_id)
    await state.clear()
    await message.answer("Баннер добавлен/изменен.", reply_markup=ADMIN_MAIN_KB)


@admin_content_router.message(AddBanner.image)
async def add_banner_two(message: types.Message, state: FSMContext):
    await message.answer("Отправьте фото или напишите 'отмена'")


@admin_content_router.callback_query(
    AdminCallback.filter(F.menu_name == "catalog"))
async def starting_at_product(callback: CallbackQuery, session: AsyncSession):
    """Выводит категории каталога"""
    await callback.answer()
    categories = await orm_get_categories(session)
    btns = {
        category.name: f"category_{category.id}" for category in categories}
    await callback.message.edit_text(
        "<strong>Выберете категорию:</strong>",
        reply_markup=get_callback_btns(btns=btns),
    )


@admin_content_router.callback_query(F.data.startswith("category_"))
async def starting_at_product(callback: CallbackQuery, session: AsyncSession):
    """Выводит все продукты в указанной категории"""
    category_id = callback.data.split("_")[-1]
    for product in await orm_get_products_admin(session, int(category_id)):
        await callback.message.answer_photo(
            product.image,
            caption=f"<strong>{product.name}\
            </strong>\n{product.description}\
            \nСтоимость: {round(product.price, 2)}\
            \n{'<b>Продукт находится в корзине.</b>' if product.is_active == False else 'Актуальный продукт.'}",
            reply_markup=get_callback_btns(
                btns={
                    "Удалить" if product.is_active else "Удалить насовсем": (
                        f"delete_{product.id}"
                        if product.is_active
                        else f"remove_{product.id}"
                    ),
                    "Изменить" if product.is_active else "Восстановить 🔄": (
                        f"change_{product.id}"
                        if product.is_active
                        else f"recove_{product.id}"
                    ),
                },
                sizes=(2,),
            ),
        )
    await callback.answer()
    await callback.message.answer("Список продуктов📋", reply_markup=ADMIN_MAIN_KB)


@admin_content_router.callback_query(F.data.startswith("delete_"))
async def delete_product_callback(
        callback: types.CallbackQuery, session: AsyncSession):
    """Удаляет продукт(Мягкое удаление)"""
    product_id = callback.data.split("_")[-1]
    await orm_delete_product(session, int(product_id))
    await callback.answer("Продукт добавлен в корзину.")
    await callback.message.answer(
        "<b>Продукт добавлен в корзину! 🗑️</b>\
                                    \n❗При удалении продукта насовсем - все покупки пользователей с этим продуктом станут недоступны.",
        reply_markup=ADMIN_MAIN_KB,
    )
    # Удаление продукта из корзины всех пользователей
    await orm_delete_from_cart_all_users(session, int(product_id))


@admin_content_router.callback_query(F.data.startswith("recove_"))
async def recove_product_callback(
        callback: types.CallbackQuery, session: AsyncSession):
    """Восстанавливает продукт"""
    product_id = callback.data.split("_")[-1]
    await orm_recove_product(session, int(product_id))
    await callback.answer("Продукт восстановлен.")
    await callback.message.answer(
        "<b>Продукт восстановлен! ✅</b>", reply_markup=ADMIN_MAIN_KB
    )


@admin_content_router.callback_query(F.data.startswith("remove_"))
async def remove_product(callback: types.CallbackQuery, session: AsyncSession):
    """Полное удаление продукта из бд"""
    product_id = callback.data.split("_")[-1]
    # await orm_remove_product(session, int(product_id))
    await callback.answer("Команда недоступна.", show_alert=True)
    # await callback.message.answer(f"<b>Продукт удален
    # насовсем.</b>",reply_markup=ADMIN_MAIN_KB)


@admin_content_router.callback_query(StateFilter(None),
                                     F.data.startswith("change_"))
async def change_product_callback(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    """Изменяет название продукта"""
    product_id = callback.data.split("_")[-1]
    product_for_change = await orm_get_product(session, int(product_id))
    AddProduct.product_for_change = product_for_change
    await callback.answer()
    await callback.message.answer(
        "Введите название продукта", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


@admin_content_router.callback_query(
    StateFilter(None), AdminCallback.filter(F.menu_name == "add_product")
)
async def add_product(callback: types.CallbackQuery, state: FSMContext):
    """Добавляет название продукта"""
    await callback.message.delete()
    await callback.message.answer(
        "Введите название продукта", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


@admin_content_router.message(StateFilter("*"), Command("отмена"))
@admin_content_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    """Сбрасывает состояние"""
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddProduct.product_for_change:
        AddProduct.product_for_change = None
    await state.clear()
    await message.answer("<b>Действия отменены</b>", reply_markup=ADMIN_MAIN_KB)


@admin_content_router.message(StateFilter("*"), Command("назад"))
@admin_content_router.message(StateFilter("*"), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    """Возвращает на шаг назад"""
    current_state = await state.get_state()

    if current_state == AddProduct.name:
        await message.answer(
            'Возвращаться некуда, введите название продукта или напишите "отмена"'
        )
        return

    previous = None
    for step in AddProduct.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(
                f"Вы вернулись к прошлому шагу: \n {AddProduct.texts[previous.state]}"
            )
            return
        previous = step


@admin_content_router.message(AddProduct.name, or_f(F.text, F.text == "."))
async def add_name(message: types.Message, state: FSMContext):
    """Обрабатывает название продукта"""
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(name=AddProduct.product_for_change.name)
    else:
        if len(message.text) >= 100:
            await message.answer(
                "Название продукта не должно превышать <b>100 символов</b>. \nВведите название заново."
            )
            return
    await state.update_data(name=message.text)
    await message.answer("Введите описание продукта")
    await state.set_state(AddProduct.description)


@admin_content_router.message(AddProduct.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели не допустимые данные, введите название продукта <b>текстом</b>"
    )


@admin_content_router.message(AddProduct.description,
                              or_f(F.text, F.text == "."))
async def add_description(
    message: types.Message, state: FSMContext, session: AsyncSession
):
    """Обработка описания продукта"""
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(description=AddProduct.product_for_change.description)
    else:
        if 4 >= len(message.text):
            await message.answer("Слишком короткое описание.\nВведите описание заново.")
            return
        await state.update_data(description=message.text)

    categories = await orm_get_categories(session)
    btns = {category.name: str(category.id) for category in categories}
    await message.answer(
        "Выберете категорию продукта.", reply_markup=get_callback_btns(btns=btns)
    )
    await state.set_state(AddProduct.category)


@admin_content_router.message(AddProduct.description)
async def add_description2(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели некорректные данные, введите описание продукта <b>текстом</b>"
    )


@admin_content_router.callback_query(AddProduct.category)
async def category_choice(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    """Обрабатывает категорию продукта"""
    try:
        category_ids = [category.id for category in await orm_get_categories(session)]

        chosen_category = int(callback.data)

        if chosen_category in category_ids:
            await callback.answer()

            await state.update_data(category=chosen_category)

            if chosen_category == 1:
                await state.update_data(link=EVENT_CHAT)
                await callback.message.answer(
                    "Теперь введите стоимость продукта.\n<b>Только цифры без лишних символов.</b>"
                )
                await state.set_state(AddProduct.price)
            elif chosen_category == 2:
                await callback.message.answer(
                    "Введите ID группы\n<b>Пример: -1234567890000</b>"
                )
                await state.set_state(AddProduct.link)
        else:
            await callback.message.answer("Выберете категорию из кнопок.")
            await callback.answer()
    except ValueError:
        await callback.message.answer("Некорректный формат данных")
        await callback.answer()


@admin_content_router.message(AddProduct.category)
async def category_choice_two(message: types.Message, state: FSMContext):
    await message.answer("Выберете категорию из кнопок", show_alert=True)


@admin_content_router.message(AddProduct.link)
async def link_choice(message: types.Message, state: FSMContext):
    """Добавляет ссылки на чат для групповых продуктов"""
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(link=AddProduct.product_for_change.link)
    else:
        try:
            int(message.text)
        except ValueError:
            await message.answer(
                "Введите корректное значение, без букв, только цифры и знак '-'"
            )
    await state.update_data(link=message.text)
    await message.answer(
        "Теперь введите стоимость продукта.\nТолько цифры без лишних символов."
    )
    await state.set_state(AddProduct.price)


@admin_content_router.message(AddProduct.link)
async def link_choice_two(message: types.Message, state: FSMContext):
    await message.answer("Введите корректное значение.")


@admin_content_router.message(AddProduct.price, or_f(F.text, F.text == "."))
async def add_price(message: types.Message, state: FSMContext):
    """Добавляет цену продукта"""
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(price=AddProduct.product_for_change.price)
    else:
        try:
            float(message.text)
        except ValueError:
            await message.answer("Введите корректное значение стоимости, только цифры.")
            return

        await state.update_data(price=message.text)
    await message.answer("Загрузите изображение продукта")
    await state.set_state(AddProduct.image)


@admin_content_router.message(AddProduct.price)
async def add_price2(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели недопустимые данные, введите стоимость продукта корректно, <b>только цифры.</b>"
    )


@admin_content_router.message(AddProduct.image, or_f(F.photo, F.text == "."))
async def add_image(message: types.Message,
                    state: FSMContext, session: AsyncSession):
    """Добавляет фотографию продукта и очищает состояние"""
    if message.text and message.text == "." and AddProduct.product_for_change:
        await state.update_data(image=AddProduct.product_for_change.image)

    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("Отправьте фото.")
        return

    data = await state.get_data()
    try:
        if AddProduct.product_for_change:
            await orm_update_product(session, AddProduct.product_for_change.id, data)
            await message.answer("<b>Продукт изменен.</b>",reply_markup=ADMIN_MAIN_KB)
        else:
            await orm_add_product(session, data)
            await message.answer(
                "<strong>Продукт добавлен/изменен</strong>", reply_markup=ADMIN_MAIN_KB
            )
            await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка: \n{str(e)}", reply_markup=ADMIN_MAIN_KB)
    await state.clear()

    AddProduct.product_for_change = None


@admin_content_router.message(AddProduct.image)
async def add_image_two(message: types.Message, state: FSMContext):
    await message.answer("Отправьте, пожалуйста, <b>фото</b>")


@admin_content_router.callback_query(
    AdminCallback.filter(F.menu_name == "promocode"))
async def starting_at_product(
        callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Вывод список всех промокодов"""
    await callback.answer()
    user_id = callback.from_user.id
    # Список с id
    sent_messages = []
    promocodes = await orm_get_all_promocodes(session)
    for promo in promocodes:
        promo_text = (
            f"\n🎟 <b>Промокод:</b> <code>{promo.code}</code>\n"
            f"📝 <b>Описание:</b> {promo.description}\n"
            f"💸 <b>Скидка %:</b> {promo.discount_value}\n "
            f"📌 <b>Значение:</b> {promo.discount_type}\n"
            f"🔹 <b>Статус:</b> {'активен ✅' if promo.is_active else 'неактивен ❌'}"
        )
        msg = await bot.send_message(
            chat_id=user_id,
            text=promo_text,
            reply_markup=get_callback_btns(
                btns={
                    "Деактивировать 🔄": f"deactivate_{promo.id}",
                    "Закрыть": f"close_{promo.id}",
                },
                sizes=(2,),
            ),
        )
        sent_messages.append(msg.message_id)

    await callback.message.edit_text(
        f"<b>📌 Актуальный список промокодов: </b>\
                                        \nПользователи могут использовать только <b>активные промокоды.</b>\
                                        \nДля копирования промокода достаточно просто нажать на него.\
                                        \nДля вовзрата на главную страницу - кнопочка ниже.⬇️",
        reply_markup=get_admin_promo_action_btn(),
    )


@admin_content_router.callback_query(F.data.startswith("close_"))
async def closed_promocode_window(callback: types.CallbackQuery):
    """Обрабокта закрытия сообщения с промокодом"""
    await callback.answer("")
    callback.data.split("_")[-1]
    await callback.message.delete()


@admin_content_router.callback_query(F.data.startswith("deactivate_"))
async def delete_promocode_callback(
    callback: types.CallbackQuery, session: AsyncSession
):
    """Деактивация промокода - изменение поля is_active = False"""
    await callback.answer("Промокод деактивирован!", show_alert=True)
    await callback.message.delete()
    promocode_id = callback.data.split("_")[-1]
    await orm_deactivate_promocode(session, int(promocode_id))


@admin_content_router.callback_query(
    StateFilter(None), AdminCallback.filter(F.menu_name == "add_promo")
)
async def add_promocode(callback: types.CallbackQuery, state: FSMContext):
    """Вход в процедуру добавления промокода"""
    await callback.message.delete()
    await callback.message.answer(
        "Введите название промокода.\n<b>Пример: FILIPPOVASCHOOL2025</b>\nДля выхода напишите <b>'отмена'</b>",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(AddPromocode.name)


@admin_content_router.message(AddPromocode.name)
async def add_promocode_name(message: types.Message, state: FSMContext):
    """Ввод названия промокода"""
    if len(message.text) >= 20:
        await message.answer(
            "Название промокода не должно превышать <b>20 символов</b>.\nВведите название заново."
        )
        return
    await state.update_data(name=message.text)
    await message.answer(
        "Введите описание промокода.\nКак написано ⬇️, это обязательно\
                                                        <b>Скидка на категорию индивидуальных/групповых продуктов - 10%/20%/30%.</b>"
    )
    await state.set_state(AddPromocode.description)


@admin_content_router.message(AddPromocode.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели некорректные данные, введите название промокода в соответствии с примером<b>FILIPPOVASCHOOL2025</b>"
    )


@admin_content_router.message(AddPromocode.description)
async def add_description(
    message: types.Message, state: FSMContext, session: AsyncSession
):
    """Обработка описания промокода"""
    if 2 >= len(message.text):
        await message.answer("Слишком короткое описание.\nВведите описание заново.")
        return
    await state.update_data(description=message.text)
    await message.answer(
        "Введите категорию промокода из списка: - <b>'individual, group, exclusive, gift(Подарочная сессия)'</b>"
    )
    await state.set_state(AddPromocode.discount_type)


@admin_content_router.message(AddPromocode.description)
async def add_description2(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели некорректные данные, введите описание промокода <b>текстом</b>"
    )


@admin_content_router.message(AddPromocode.discount_type)
async def add_discount_type(message: types.Message, state: FSMContext):
    """Обработка категории промокода"""
    if message.text in type_list:
        await state.update_data(discount_type=message.text)
        await message.answer(
            "Введите значение скидки.\n<b>Только число</b>\
                                Для individual : 10 - 50, group:  5 -15, exclusive,gift:  100"
        )
        await state.set_state(AddPromocode.discount_value)
    else:
        await message.answer(
            "Введите категорию промокода из списка: - <b>'individual, group, exclusive, gift'</b>"
        )


@admin_content_router.message(AddPromocode.discount_type)
async def add_discount_type_incorrect(
        message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели некорректные данные, введите категорию промокода <b>текстом</b>"
    )


@admin_content_router.message(AddPromocode.discount_value)
async def add_price(message: types.Message, state: FSMContext):
    """Добавляет значение скидки промокода"""
    try:
        float(message.text)
    except ValueError:
        await message.answer("Введите корректное значение скидки <b>'цифрами'</b>.")
        return
    await state.update_data(discount_value=message.text)
    await message.answer("Введите количество использований.")
    await state.set_state(AddPromocode.usage)


@admin_content_router.message(AddPromocode.discount_value)
async def add_price2(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели некорректные данные, введите значение скидки корректно, <b>только цифры.\nПример: 20</b>"
    )


@admin_content_router.message(AddPromocode.usage)
async def add_usage(message: types.Message,
                    state: FSMContext, session: AsyncSession):
    """Обрабатывает количество использований промокода(Ввод) и очищает состояние"""
    try:
        int(message.text)
    except ValueError:
        await message.answer(
            "Введите корректное значение использований <b>'цифрами, без лишних символов'</b>."
        )
        return
    await state.update_data(usage=message.text)
    data = await state.get_data()
    await orm_add_promocode(session, data)
    await message.answer("Промокод добавлен.", reply_markup=ADMIN_MAIN_KB)
    await state.clear()


@admin_content_router.message(AddPromocode.usage)
async def add_usage_incorrect(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы ввели некорректные данные, введите значение использований корректно, <b>только цифры.\nПример: 20</b>"
    )

from dataclasses import dataclass
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

"""Модуль для клавиатуры админ панели"""


class AdminCallback(CallbackData, prefix="adm"):

    menu_name: str


@dataclass
class AdminButton:
    text: str
    menu_name: str
    icon: str = ""

    def build(self) -> InlineKeyboardButton:

        text = f"{self.icon} {self.text}" if self.icon else self.text
        return InlineKeyboardButton(
            text=text, callback_data=AdminCallback(
                menu_name=self.menu_name).pack()
        )


ADMIN_MENU_BUTTONS = [
    AdminButton("Изменить статус", "support", "🔄"),
    AdminButton("Найти пользовтеля", "users", "👥"),
    AdminButton("Каталог", "catalog", "🛍️"),
    AdminButton("Добавить баннер", "banner", "🖼️"),
    AdminButton("Добавить продукт", "add_product", "➕"),
    AdminButton("Промокоды", "promocode", "🎟️"),
    AdminButton("Статистика", "statistics", "📊"),
    AdminButton("Создать рассылку", "sendler", "✉️"),
]

ADMIN_MAIN = [AdminButton("На главную", "main", "🏠︎")]

ADMIN_GET_USERS_ACTION = [
    AdminButton("На главную", "main", "🏠︎"),
    AdminButton("Написать", "send_to_user", "📩"),
    AdminButton("Забанить", "baned", "⛔"),
]

ADMIN_GET_PROMO_ACTION = [
    AdminButton("На главную", "main", "🏠︎"),
    AdminButton("Добавить промокод", "add_promo", "🆕"),
]

ADMIN_GET_SENDLER_ACTION = [
    AdminButton("На главную", "main", "🏠︎"),
    AdminButton("Начать рассылку", "start_broadcast_", "🔊"),
]


# Main Menu
def get_admin_menu_btns(
        *, sizes: tuple[int, ...] = (2, 2, 2)) -> InlineKeyboardMarkup:
    """Выводит кнопки главного меню"""
    builder = InlineKeyboardBuilder()

    for btn in ADMIN_MENU_BUTTONS:
        builder.add(btn.build())

    return builder.adjust(*sizes).as_markup()


# 1 кнопка
def get_admin_main_btn(
        *, sizes: tuple[int, ...] = (1,)) -> InlineKeyboardMarkup:
    """Возвращает на щаг назад, 1 кнопка"""
    builder = InlineKeyboardBuilder()

    for btn in ADMIN_MAIN:
        builder.add(btn.build())

    return builder.adjust(*sizes).as_markup()


def get_admin_user_action_btn(
    *, sizes: tuple[int, ...] = (2, 2, 2)
) -> InlineKeyboardMarkup:
    """Вывод кнопки для действий с пользователем"""
    builder = InlineKeyboardBuilder()

    for btn in ADMIN_GET_USERS_ACTION:
        builder.add(btn.build())

    return builder.adjust(*sizes).as_markup()


def get_admin_promo_action_btn(
    *, sizes: tuple[int, ...] = (2,)
) -> InlineKeyboardMarkup:
    """Выводит кнопки действий с промокодом"""
    builder = InlineKeyboardBuilder()

    for btn in ADMIN_GET_PROMO_ACTION:
        builder.add(btn.build())

    return builder.adjust(*sizes).as_markup()


def get_admin_sendler_action_btns(
    *, sizes: tuple[int, ...] = (2,)
) -> InlineKeyboardMarkup:
    """Выводит кнопки создания рассылки"""
    builder = InlineKeyboardBuilder()

    for btn in ADMIN_GET_SENDLER_ACTION:
        builder.add(btn.build())

    return builder.adjust(*sizes).as_markup()


def get_callback_btns(*, btns: dict[str, str], sizes: tuple[int] = (2,)):
    """Универсальный метод для реализации кнопок на ходу"""
    keyboard = InlineKeyboardBuilder()

    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()

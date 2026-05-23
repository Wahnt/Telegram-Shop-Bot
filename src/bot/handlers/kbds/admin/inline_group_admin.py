from dataclasses import dataclass
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


"""Модуль инлайн клавиатуры для работы с заказами"""


class AdminGroupCallback(CallbackData, prefix="adm"):

    menu_name: str


@dataclass
class AdminGroupButton:
    text: str
    menu_name: str
    icon: str = ""

    def build(self) -> InlineKeyboardButton:

        text = f"{self.icon} {self.text}" if self.icon else self.text
        return InlineKeyboardButton(
            text=text, callback_data=AdminGroupCallback(
                menu_name=self.menu_name).pack()
        )


ADMIN_GROUP_BUTTONS = [
    AdminGroupButton("Связаться", "connect", "🔗"),
    AdminGroupButton("Поменять статус", "pinned", "🔄"),
]


def get_admin_group_btns(
        *, sizes: tuple[int, ...] = (2, 2, 2)) -> InlineKeyboardMarkup:
    """Кнопки для работы с сообщениями заказов"""
    builder = InlineKeyboardBuilder()

    for btn in ADMIN_GROUP_BUTTONS:
        builder.add(btn.build())

    return builder.adjust(*sizes).as_markup()

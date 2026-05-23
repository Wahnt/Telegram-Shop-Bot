from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class SupportCallback(CallbackData, prefix="support"):

    menu_name: str


# Admin
def get_admin_btns(*, sizes: tuple[int] = (1,)):
    keyboard = InlineKeyboardBuilder()
    btns = {
        "Ответить пользователю": "answer_to_user",
    }

    for text, menu_name in btns.items():
        if menu_name == "answer_to_user":
            keyboard.add(
                InlineKeyboardButton(
                    text=text, callback_data=SupportCallback(
                        menu_name=menu_name).pack()
                )
            )
    return keyboard.adjust(*sizes).as_markup()


# User
def get_user_btns(*, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    btns = {
        "Начать сеанс": "find_support",
        "Закрыть": "answer_end",
    }

    for text, menu_name in btns.items():
        if menu_name == "find_support":
            keyboard.add(
                InlineKeyboardButton(
                    text=text, callback_data=SupportCallback(
                        menu_name=menu_name).pack()
                )
            )
        elif menu_name == "answer_end":
            keyboard.add(
                InlineKeyboardButton(
                    text=text, callback_data=SupportCallback(
                        menu_name=menu_name).pack()
                )
            )
    return keyboard.adjust(*sizes).as_markup()


# User
def ask_to_support_btns(*, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    btn = {
        "Написать": "send_message",
        "Закрыть": "close",
    }

    for text, menu_name in btn.items():
        if menu_name == "send_message":
            keyboard.add(
                InlineKeyboardButton(
                    text=text, callback_data=SupportCallback(
                        menu_name=menu_name).pack()
                )
            )
        elif menu_name == "close":
            keyboard.add(
                InlineKeyboardButton(
                    text=text, callback_data=SupportCallback(
                        menu_name=menu_name).pack()
                )
            )
    return keyboard.adjust(*sizes).as_markup()

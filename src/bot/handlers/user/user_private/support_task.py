import asyncio
from aiogram import Bot
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.bot.handlers.kbds.user.inline_support import ask_to_support_btns
from src.core.cache.cache import cache

"""Модуль для фоновой задачи присоединения администратора"""


async def check_session_status(
        user_id: int, stop_event: asyncio.Event) -> bool:
    """Каждый 0.5 секунд проверяет кеш на наличие ID администратора"""
    while not stop_event.is_set():
        cache_data = await cache.get(f"chat_session:{user_id}")
        # Если админ добавился
        if cache_data and cache_data.get("admin_id"):
            admin_id = cache_data["admin_id"]
            return True
        await asyncio.sleep(0.5)
    return False


async def handle_support_request(
        bot: Bot, session: AsyncSession, user_id: int) -> bool:
    """Запускает фоновую задачу и уведомляет пользователя
    - если администратор не найден - стопает задачу, уведомляет пользователя"""
    stop_event = asyncio.Event()
    animation_msg = await bot.send_message(
        user_id, "⏳ Ожидаем ответа администратора..."
    )
    timeout_minutes = 1
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=timeout_minutes)

    status_checker = asyncio.create_task(
        check_session_status(user_id, stop_event))

    while datetime.now() < end_time:
        # Дожидаемся выполнения status_checker
        done, pending = await asyncio.wait(
            [status_checker], timeout=60, return_when=asyncio.FIRST_COMPLETED
        )

        if status_checker.done():
            if status_checker.result():
                succes = True
                await bot.delete_message(user_id, animation_msg.message_id)
                return True
            break
    # Если администратор не появился - уведомляем пользователя
    stop_event.set()
    await status_checker

    if datetime.now() >= end_time:
        await bot.delete_message(user_id, animation_msg.message_id)
        await bot.send_message(
            user_id,
            "⏳ Приносим извинения за ожидание! Все администраторы заняты. "
            "Попробуйте позже или оставьте сообщение.",
            reply_markup=ask_to_support_btns(),
        )
        return False

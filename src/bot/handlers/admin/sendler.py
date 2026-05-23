import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

success_ids = []


async def start_broadcast(
    bot: Bot,
    session: AsyncSession,
    user_ids: list[int],
    text: str,
    disable_notification: bool = False,
    delay: float = 0.1,
) -> dict:
    """Реализует рассылку пользователям с активным(True) поле is_active"""
    result = {
        "success": 0,
        "failed": 0,
        "blocked": 0,
        "success_ids": [],
        "blocked_ids": [],
    }

    for chat_id in user_ids:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text[:4096],
                disable_notification=disable_notification,
            )
            result["success"] += 1
            result["success_ids"].append(chat_id)
            await asyncio.sleep(delay)

        except TelegramRetryAfter as e:

            wait_time = e.retry_after
            await asyncio.sleep(wait_time)

            try:
                await bot.send_message(chat_id=chat_id, text=text)
                result["success"] += 1
                result["success_ids"].append(chat_id)
            except Exception as e:
                result["failed"] += 1
                if "bot was blocked" in str(e).lower():
                    result["blocked"] += 1
                    result["blocked_ids"].append(chat_id)

        except Exception as e:
            result["failed"] += 1
            if "bot was blocked" in str(e).lower():
                result["blocked"] += 1
                result["blocked_ids"].append(chat_id)
            continue

    return result

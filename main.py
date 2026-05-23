from src.bot.bot_data.bot_cmd_list import private
from src.bot.handlers.service.maintenance_mode import maintenance_router
from src.bot.handlers.user.user_group.user_group import user_group_router
from src.bot.handlers.user.user_private.user_support import user_support_router
from src.bot.handlers.user.user_catalog.user_private_catalog import user_private_catalog_router
from src.bot.handlers.user.user_private.user_private import user_private_router
from src.bot.handlers.admin.admin_group import admin_group_router
from src.bot.handlers.admin.admin_private_content import admin_content_router
from src.bot.handlers.admin.admin_private import admin_router
from src.bot.handlers.admin.admin_main_private import admin_main_router

from src.core.database.engine import create_db, drop_db, session_maker
from src.bot.middlewares.privacy import PrivacyConsentMiddleware
from src.bot.middlewares.database import DataBaseSession
from src.bot.middlewares.maintenance import MaintenanceMiddleware

import asyncio
import os
import logging
from contextlib import asynccontextmanager

from aiohttp import ClientSession
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from dotenv import find_dotenv, load_dotenv
import redis.asyncio as redis
from src.core.cache.cache import cache, state_manager, redis_connection
from src.core.config.settings import app_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

WEBHOOK_MODE = os.getenv('WEBHOOK_MODE', 'False').lower() == 'true'
WEBHOOK_PATH = f"/webhook/{os.getenv('TOKEN')}"
WEBHOOK_URL = f"https://{os.getenv('DOMAIN')}{WEBHOOK_PATH}" if os.getenv('DOMAIN') else None

bot = Bot(
    token=app_settings.bot_token_str,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
bot.my_admins_list = []
dp = Dispatcher(storage=state_manager.storage)

dp.update.middleware(DataBaseSession(session_pool=session_maker))
dp.message.middleware(PrivacyConsentMiddleware(cache))
dp.callback_query.middleware(PrivacyConsentMiddleware(cache))

dp.include_router(maintenance_router)
dp.include_router(admin_main_router)
dp.include_router(admin_router)
dp.include_router(admin_content_router)
dp.include_router(admin_group_router)
dp.include_router(user_private_router)
dp.include_router(user_private_catalog_router)
dp.include_router(user_support_router)
dp.include_router(user_group_router)

async def on_startup(bot: Bot):
    await create_db()
    await cache.init()
    await redis_connection.ping()
    if WEBHOOK_MODE and WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
        logger.info(f"Webhook настроен на URL: {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    logger.warning("Бот стоп")
    if WEBHOOK_MODE:
        await bot.delete_webhook()
    await bot.session.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup(bot)
    yield
    await on_shutdown(bot)
    await ClientSession().close()

app = FastAPI(lifespan=lifespan) if WEBHOOK_MODE else None

if WEBHOOK_MODE:
    @app.post(WEBHOOK_PATH)
    async def bot_webhook(request: Request):
        try:
            # 1. Получаем и валидируем сырые данные
            raw_data = await request.body()
            logger.debug(f"Raw webhook data: {raw_data.decode()}")
            json_data = await request.json()
            # 2. Валидация структуры Update
            update = Update.model_validate(json_data)
            logger.debug(f"Parsed update: {update}")      
            # 3. Обработка через диспетчер
            try:
                async with session_maker() as session:
                    await dp.feed_update(bot=bot, update=update, session=session)
                
                return {"status": "ok", "update_id": update.update_id}
                
            except Exception as e:
                logger.error(f"Processing error: {str(e)}", exc_info=True)
                return {"status": "error", "detail": "Update processing failed"}, 500
                
        except Exception as e:
            logger.critical(f"Critical webhook error: {str(e)}", exc_info=True)
            return {"status": "error", "detail": "Internal server error"}, 500

async def setup_bot_commands():
    await bot.set_my_commands(commands=private,scope=types.BotCommandScopeAllPrivateChats())

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await setup_bot_commands()
    if WEBHOOK_MODE:
        logger.info("Запуск в режиме webhook")
    else:
        logger.info("Запуск в режиме polling")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, skip_updates=False,
                            allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        if WEBHOOK_MODE:
            import uvicorn
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8000
            )
        else:
            asyncio.run(main())
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        raise


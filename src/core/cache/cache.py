from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
import redis.asyncio as redis
from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from functools import wraps
import pickle
import asyncio
from src.core.config.settings import redis_settings

class StateManager:
    """Менеджер для работы с состоянием"""

    def __init__(self, redis_connection):
        """Инициализация хранилища"""
        self.storage = RedisStorage(
            redis=redis_connection, state_ttl=28800, data_ttl=28800  # 8 часов
        )

    async def reset_user_state(self, bot: Bot, user_id: int):
        """Сброс состояния"""
        storage_key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id)
        await self.storage.set_state(storage_key, None)
        await self.storage.set_data(storage_key, {})


class CacheService:
    """Кэш сервис, отвечает за работу с кэшем"""

    def __init__(self):
        self.redis: Redis = None
        self.lock = asyncio.Lock()
        self.consent_ttl = 86400

    async def init(self):
        """Инициализация подключения"""
        self.redis = redis.Redis(**redis_settings.config)

    async def get(self, key: str):
        """Получить кеш"""
        data = await self.redis.get(key)
        return pickle.loads(data) if data else None

    async def set(self, key: str, value, ttl: int = 300):
        """Добавляет кэш"""
        async with self.lock:
            await self.redis.set(key, pickle.dumps(value), ex=ttl)

    async def invalidate(self, key: str):
        """Удаляет запись кэша"""
        await self.redis.delete(key)

    async def cache_user_consent(self, user_id: int, has_consent: bool):
        """Отдельный метод для кэшироваения согласия пользователя"""
        async with self.lock:
            await self.redis.set(
                f"user_consent:{user_id}",
                pickle.dumps(has_consent),
                ex=self.consent_ttl,
            )

    async def get_user_consent(self, user_id: int):
        """Метод для получения согласия пользователя"""
        data = await self.redis.get(f"user_consent:{user_id}")
        return pickle.loads(data) if data else None

    async def invalidate_user_consent(self, user_id: int):
        """Метод для удаления согласия пользователя"""
        await self.redis.delete(f"user_consent:{user_id}")


cache = CacheService()

redis_connection = redis.Redis(**redis_settings.config)

state_manager = StateManager(redis_connection)


# Декоратор для orm запросов
def cached(ttl: int = 60, dynamic_key: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = args[1] if len(args) > 1 else kwargs.get("user_id")
            cache_key = f"{func.__name__}:{user_id}"

            cached_data = await cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            result = await func(*args, **kwargs)

            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator

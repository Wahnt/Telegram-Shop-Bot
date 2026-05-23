import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event

from src.core.database.models.models import Base , ChatSession
from src.core.database.orm_queries.catalog import orm_create_categories, orm_add_banner_description

from src.bot.bot_data.text_for_db import categories, description_for_info_pages
from src.core.config.settings import db_settings

# Инициализация
engine = create_async_engine(db_settings.dsn, echo=True)

# Фабрика асинхронных сессий
session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db():
    """Создает таблицы в бд и заполняет начальными данными"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        await orm_create_categories(session, categories)
        await orm_add_banner_description(session, description_for_info_pages)


async def drop_db():
    """Польностью удаляет все таблицы из бд"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

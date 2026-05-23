from datetime import datetime, timedelta
from sqlalchemy import select, func, distinct, extract
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.models.models import (
    User,
    Product,
    Purchase,
    PurchaseItem,
    Payment,
    PromocodeUsage,
    Promocode,
)

"""Модуль для работы с аналитикой и статистикой магазина.

Содержит функции для получения:
- Статистики пользователей
- Финансовых показателей
- Продуктовой аналитики
- Данных по промокодам
"""


async def get_total_users(session: AsyncSession) -> int:
    """Получает общее количество активных пользователей"""
    result = await session.execute(select(func.count(User.id)))
    return result.scalar()


async def get_new_users(session: AsyncSession, period: str = "day") -> int:
    """Получает количество новых пользователей за указанный период"""
    if period == "day":
        delta = timedelta(days=1)

    elif period == "week":
        delta = timedelta(weeks=1)

    else:
        delta = timedelta(days=1)

    result = await session.execute(
        select(
            func.count(
                User.id)).where(
            User.created >= datetime.now() -
            delta)
    )

    return result.scalar()


async def get_active_users(session: AsyncSession, days: int = 30) -> int:
    """Получет количество активных пользователей совершавших покупки"""
    result = await session.execute(
        select(func.count(distinct(Purchase.user_id))).where(
            Purchase.created >= datetime.now() - timedelta(days=days)
        )
    )
    return result.scalar()


async def get_conversion_rate(session: AsyncSession) -> float:
    """Рассчитывает конверсию пользователей в покупку"""
    total_users = await session.scalar(select(func.count(User.id)))
    buyers = await session.scalar(select(func.count(distinct(Purchase.user_id))))
    return round((buyers / total_users) * 100, 2) if total_users else 0


async def get_revenue_stats(session: AsyncSession) -> dict:
    """Получает финансовую статистику"""
    # Текущий месяц
    month_revenue = await session.scalar(
        select(func.sum(Payment.amount)).where(
            extract("month", Payment.created) == datetime.now().month
        )
    )

    avg_check = await session.scalar(select(func.avg(Payment.amount)))

    return {"month": month_revenue or 0, "avg": round(
        avg_check, 2) if avg_check else 0}


async def get_top_products(session: AsyncSession, limit: int = 3) -> list:
    """Получает топ продуктов по выручке"""
    result = await session.execute(
        select(
            Product.name,
            func.count(PurchaseItem.id).label("sales"),
            func.sum(PurchaseItem.product_price * PurchaseItem.quantity).label(
                "revenue"
            ),
        )
        .join(PurchaseItem, Product.purchases_items)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(PurchaseItem.product_price * PurchaseItem.quantity).desc())
        .limit(limit)
    )
    return [dict(row) for row in result.mappings()]


async def get_promo_stats(session: AsyncSession) -> dict:
    """Получает статистику по промокодам"""
    total_used = await session.scalar(select(func.count(PromocodeUsage.id)))

    top_promo = await session.execute(
        select(Promocode.code, func.count(PromocodeUsage.id).label("uses"))
        .join(PromocodeUsage.promocode)
        .group_by(Promocode.id)
        .order_by(func.count(PromocodeUsage.id).desc())
        .limit(1)
    )
    top_promo_data = top_promo.first()

    return {
        "total_used": total_used or 0,
        "top_promo": (
            f"{top_promo_data.code} (\nКоличество активаций: {top_promo_data.uses})"
            if top_promo_data
            else "Нет данных"
        ),
    }

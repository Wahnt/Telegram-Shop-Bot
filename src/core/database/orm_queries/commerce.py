from decimal import Decimal
from sqlalchemy import select, update, delete, exists, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.models.models import Payment, Purchase, PurchaseItem, Promocode, PromocodeUsage, User

"""Модуль для работы с платежами и покупками пользователей
Содержит функции для:
- Создания платежей и связанных с ним покупок и промокодов
- Получение истории платежей и покупок пользователей
"""


async def create_payment_with_purchase(
    session: AsyncSession,
    user_id: int,
    payment_data: dict,
    carts: list,
    promocode: Promocode | None = None
) -> tuple[Payment, Purchase]:
    """Создает платеж и связанную с ним покупку с продуктами в корзине
    Обрабатывает применение промокода, если он указан. Обновляет статус использования промококда.
    Создает записи о каждом продукте в покупке с учетом возможных скидок"""
    payment = Payment(
        user_id=user_id,
        amount=Decimal(str(payment_data['amount'])),
        currency=payment_data['currency'],
        telegram_payment_id=payment_data['telegram_payment_id'],
        provider_payment_id=payment_data['provider_payment_id']
    )
    session.add(payment)
    await session.flush()

    # Создаем покупку
    purchase = Purchase(
        user_id=user_id,
        payment_id=payment.id,
        promocode_id=promocode.id if promocode else None
    )
    session.add(purchase)
    await session.flush()

    if promocode:
        usage_query = await session.execute(
            select(PromocodeUsage)
            .where(
                and_(
                    PromocodeUsage.user_id == user_id,
                    PromocodeUsage.promocode_id == promocode.id,
                    PromocodeUsage.status_usage == True
                )
            )
            .order_by(PromocodeUsage.id.desc())
            .limit(1)
        )
        promocode_usage = usage_query.scalar_one_or_none()

        if promocode_usage:
            promocode_usage.status_usage = False
            session.add(promocode_usage)

    # Обрабатываем каждый товар в корзине
    for item in carts:
        # Явно загружаем продукт если не загружен
        if not hasattr(item, 'product'):
            await session.refresh(item, ['product'])

        original_price = Decimal(str(item.product.price))
        final_price = original_price

        # Применяем скидку если есть промокод и продукт нужной категории
        if promocode:
            if (promocode.discount_type == "individual" and item.product.category_id == 1) or \
                    (promocode.discount_type == "group" and item.product.category_id == 2):
                discount = Decimal(str(promocode.discount_value))
                final_price = original_price * (1 - discount / 100)
                final_price = final_price.quantize(Decimal('0.00'))

        # Создаем позицию в покупке
        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            product_id=item.product.id,
            product_name=item.product.name,
            product_price=original_price,
            final_price=final_price,
            product_status=item.product.is_active,
            quantity=item.quantity
        )
        session.add(purchase_item)

    await session.commit()

    return payment, purchase


async def get_user_payments(session: AsyncSession,
                            user_id: int) -> list[Payment]:
    """Получает все платежи пользователя с детализацией покупок"""
    query = (
        select(Payment)
        .where(Payment.user_id == user_id)
        .options(
            joinedload(Payment.purchases)
            .joinedload(Purchase.purchases_items)
            .order_by(Payment.id.desc())
        ))

    result = await session.execute(query)
    payments = result.scalars().unique().all()

    return payments


async def get_user_purchases(session: AsyncSession,
                             user_id: int) -> list[PurchaseItem]:
    """Получает все покупки пользователя с полной информацией
    Пользовательская функция"""

    query = (
        select(Purchase)
        .where(Purchase.user_id == user_id)
        .options(
            joinedload(
                Purchase.purchases_items).joinedload(
                PurchaseItem.product),
            joinedload(Purchase.payment),
            joinedload(Purchase.promocode)
        )
        .order_by(Purchase.id.desc())
        .limit(5) # Первые 5 покупок
    )

    result = await session.execute(query)
    return result.unique().scalars().all()


async def get_user_with_relations(session: AsyncSession,
                                  user_id: int | None = None,
                                  username: str | None = None,) -> User | None:
    """Возвращает пользователя с подгрузкой платежей и покупок"""

    query = select(User).options(
        selectinload(User.payments).options(
            selectinload(Payment.purchases).options(
                selectinload(Purchase.purchases_items).options(
                    joinedload(PurchaseItem.product)
                )
            )
        ),

        selectinload(User.purchases).options(
            selectinload(Purchase.purchases_items).options(
                joinedload(PurchaseItem.product)
            )
        )
    )

    if user_id is not None:
        query = query.where(User.user_id == user_id)
    elif username is not None:
        query = query.where(User.username == username)

    result = await session.execute(query)
    return result.scalar_one_or_none()

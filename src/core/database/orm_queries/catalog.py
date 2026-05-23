import logging

from typing import Optional, List
from sqlalchemy import select, update, delete, exists
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.models.models import User, Product, Category, Cart, Banner

"""Модуль содержит запросы для работы с:
- Баннерами
- Продуктами
- Категориями
- Корзинами пользователей

"""

"""Баннер"""


async def orm_add_banner_description(
        session: AsyncSession, data: dict) -> None:
    """Добавляет баннер в базу данных
    Принимает словарь {name: description} / main, catalog, cart"""
    query = select(Banner)
    result = await session.execute(query)
    if result.first():
        return

    session.add_all(
        [
            Banner(name=name, description=description)
            for name, description in data.items()
        ]
    )
    await session.commit()


async def orm_change_banner_image(
        session: AsyncSession, name: str, image: str) -> None:
    """Изменяет изображение баннера"""
    query = update(Banner).where(Banner.name == name).values(image=image)
    await session.execute(query)
    await session.commit()


async def orm_get_banner(session: AsyncSession, page: str) -> Optional[Banner]:
    """Получает баннер по названию страницы"""
    query = select(Banner).where(Banner.name == page)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_info_pages(session: AsyncSession) -> List[Banner]:
    """Получает все информационные страницы-баннеры"""
    query = select(Banner)
    result = await session.execute(query)
    return result.scalars().all()


"""Продукт"""


async def orm_add_product(session: AsyncSession, data: dict) -> None:
    """Добавляет новый продукт в бд"""
    obj = Product(
        name=data["name"],
        description=data["description"],
        link=data["link"],
        price=float(data["price"]),
        image=data["image"],
        category_id=int(data["category"]),
    )
    session.add(obj)
    await session.commit()


async def orm_get_products(session: AsyncSession,
                           category_id) -> List[Product]:
    """Получает активные продукты по категории"""
    query = select(Product).where(
        Product.category_id == int(category_id), Product.is_active == True
    )
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_products_admin(
        session: AsyncSession, category_id) -> List[Product]:
    """Получает все продукты по категории, включаа неактивные
    - для админ панели"""
    query = select(Product).where(Product.category_id == int(category_id))
    result = await session.execute(query)
    return result.scalars().all()


async def orm_recove_product(session: AsyncSession, product_id) -> None:
    """Восстанавливает удаленный продукт/Помечает как активный"""
    query = update(Product).where(
        Product.id == product_id).values(
        is_active=True)
    await session.execute(query)
    await session.commit()


async def orm_remove_product(session: AsyncSession, product_id: int) -> None:
    """Полностью удаляет продукт из базы данных"""
    query = delete(Product).where(Product.id == product_id)
    await session.execute(query)
    await session.commit()


async def orm_get_product(session: AsyncSession,
                          product_id: int) -> Optional[Product]:
    """Получает продукт по ID"""
    query = select(Product).where(Product.id == product_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_product(
        session: AsyncSession, product_id: int, data) -> None:
    """Обновляет данные продукта"""
    query = (
        update(Product)
        .where(Product.id == product_id)
        .values(
            name=data["name"],
            description=data["description"],
            price=float(data["price"]),
            image=data["image"],
            category_id=int(data["category"]),
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_product(session: AsyncSession, product_id: int) -> None:
    """Помечает продукт как неактивный(мягкое удаление)"""
    query = update(Product).where(
        Product.id == product_id).values(
        is_active=False)
    await session.execute(query)
    await session.commit()


"""Категории"""


async def orm_get_categories(session: AsyncSession) -> List[Category]:
    """Получает все категории"""
    query = select(Category)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_create_categories(
        session: AsyncSession, categories: list) -> None:
    """Создает категории"""
    query = select(Category)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Category(name=name) for name in categories])
    await session.commit()


"""Корзина"""


async def orm_add_to_cart(
    session: AsyncSession, user_id: int, product_id: int
) -> Optional[Cart]:
    """Добавляет продукт в порзину пользователя, если продукт уже есть
    увеличивает его количество на 1"""
    query = select(Cart).where(
        Cart.user_id == user_id,
        Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()
    if cart:
        cart.quantity += 1
        await session.commit()
        return cart
    else:
        session.add(Cart(user_id=user_id, product_id=product_id, quantity=1))
        await session.commit()


async def orm_get_user_carts(session: AsyncSession,
                             user_id: int) -> List[Cart]:
    """Получает корзину пользователя с полной информацией о продуктах"""
    query = (
        select(Cart)
        .filter(Cart.user_id == user_id)
        .options(joinedload(Cart.product).joinedload(Product.category))
    )
    result = await session.execute(query)
    return result.unique().scalars().all()


async def orm_delete_from_cart(
    session: AsyncSession, user_id: int, product_id: int
) -> None:
    """Удаляет продукт из корзины пользователя"""
    query = delete(Cart).where(
        Cart.user_id == user_id,
        Cart.product_id == product_id)
    await session.execute(query)
    await session.commit()


async def orm_delete_from_cart_all_users(
    session: AsyncSession, product_id: int
) -> None:
    """Удаляет продукт из корзины всех пользователей"""
    query = delete(Cart).where(Cart.product_id == product_id)
    await session.execute(query)
    await session.commit()


async def orm_delete_user_carts(session: AsyncSession, user_id) -> None:
    """Очищает корзину пользователя"""
    query = (
        delete(Cart).filter(
            Cart.user_id == user_id).options(
            joinedload(
                Cart.product))
    )
    await session.execute(query)
    await session.commit()


async def orm_reduce_product_in_cart(
    session: AsyncSession, user_id: int, product_id: int
) -> bool:
    """Ументшает количество продукта в корзине на 1
    если количество = 0, удаляет продукт"""
    query = select(Cart).where(
        Cart.user_id == user_id,
        Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()

    if not cart:
        return
    if cart.quantity > 1:
        cart.quantity -= 1
        await session.commit()
        return True
    else:
        await orm_delete_from_cart(session, user_id, product_id)
        await session.commit()
        return False

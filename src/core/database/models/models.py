from sqlalchemy import (
    DateTime,
    BigInteger,
    Boolean,
    String,
    Text,
    Integer,
    Numeric,
    func,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List
from decimal import Decimal


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class Banner(Base):
    __tablename__ = "banner"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    image: Mapped[str] = mapped_column(String(150), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # chat_id для добавления пользователей
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    image: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # true - продукт виден в каталоге, false - продукт удален, но есть в истории покупок

    category: Mapped["Category"] = relationship(backref="product")
    purchases_items: Mapped[list["PurchaseItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )


class Cart(Base):
    __tablename__ = "cart"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int]

    user: Mapped["User"] = relationship(backref="cart")
    product: Mapped["Product"] = relationship(backref="cart")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_status: Mapped[int] = mapped_column(
        Integer, default=None, nullable=True)
    accepted_privacy: Mapped[bool] = mapped_column(Boolean, default=True)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    initiated_chats: Mapped[List["ChatSession"]] = relationship(
        back_populates="user",
        foreign_keys="ChatSession.user_id",
        cascade="all, delete-orphan",
    )
    used_promocodes: Mapped[list["PromocodeUsage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    purchases: Mapped[list["Purchase"]] = relationship(
        back_populates="user",
        foreign_keys="Purchase.user_id",
        cascade="all, delete-orphan",
    )


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(4), default="RUB")
    telegram_payment_id: Mapped[str] = mapped_column(String(100), unique=True)
    provider_payment_id: Mapped[str] = mapped_column(String(100), unique=True)

    user: Mapped["User"] = relationship(back_populates="payments")
    purchases: Mapped["Purchase"] = relationship(back_populates="payment")


class Purchase(Base):
    __tablename__ = "purchase"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.user_id", ondelete="CASCADE"))
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payment.id", ondelete="CASCADE")
    )
    promocode_id: Mapped[int] = mapped_column(
        ForeignKey("promocodes.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="purchases")
    payment: Mapped["Payment"] = relationship(back_populates="purchases")
    promocode: Mapped["Promocode"] = relationship(back_populates="purchases")
    purchases_items: Mapped[list["PurchaseItem"]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan"
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchase.id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(150))
    product_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    product_status: Mapped[bool] = mapped_column(Boolean)
    quantity: Mapped[int] = mapped_column(Integer)
    final_price: Mapped[int] = mapped_column(Integer)

    purchase: Mapped["Purchase"] = relationship(
        back_populates="purchases_items")
    product: Mapped["Product"] = relationship(back_populates="purchases_items")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.user_id", ondelete="CASCADE"))
    username: Mapped[str] = mapped_column(String(32))
    first_name: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(20), default="waiting"
    )  # waiting, active, #closed - в процессе
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

    user: Mapped["User"] = relationship(
        back_populates="initiated_chats", foreign_keys=[user_id]
    )


class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(22))
    description: Mapped[str] = mapped_column(String(255))
    discount_type: Mapped[str] = mapped_column(
        String(16), nullable=True
    )  # individual/ group/ exclusive/ gift
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # коэффициент скидки
    usage: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)

    usages: Mapped[list["PromocodeUsage"]] = relationship(
        back_populates="promocode")
    purchases: Mapped[list["Purchase"]] = relationship(
        back_populates="promocode")


class PromocodeUsage(Base):
    __tablename__ = "promocodes_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.user_id", ondelete="CASCADE"))
    promocode_id: Mapped[int] = mapped_column(
        ForeignKey("promocodes.id", ondelete="CASCADE")
    )
    status_usage: Mapped[bool] = mapped_column(default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="used_promocodes")
    promocode: Mapped["Promocode"] = relationship(
        back_populates="usages", foreign_keys=[promocode_id]
    )

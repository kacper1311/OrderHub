import uuid
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import CheckConstraint, UniqueConstraint
from .enums import OrderStatus


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("channel_id", "external_order_id", name="uq_orders_channel_external_order_id"),
        CheckConstraint("total >= 0", name="ck_orders_total_non_negative"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    channel_id: uuid.UUID = Field(foreign_key="channels.id")
    external_order_id: str
    status: OrderStatus
    customer_name: str
    customer_email: str
    shipping_address: str
    total: Decimal = Field(max_digits=10, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

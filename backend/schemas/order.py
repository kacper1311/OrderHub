import uuid
from datetime import datetime
from decimal import Decimal

from sqlmodel import Field

from models.enums import OrderStatus
from schemas.base import CamelModel


class Customer(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    address: str = Field(min_length=1, max_length=500)


class OrderItemCreate(CamelModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)


class OrderCreate(CamelModel):
    channel_id: uuid.UUID
    customer: Customer
    items: list[OrderItemCreate] = Field(min_length=1)


class ChannelBrief(CamelModel):
    id: uuid.UUID
    code: str
    name: str


class OrderListItem(CamelModel):
    id: uuid.UUID
    channel: ChannelBrief
    external_order_id: str
    status: OrderStatus
    total: Decimal
    created_at: datetime


class OrderItemRead(CamelModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


class OrderDetail(CamelModel):
    id: uuid.UUID
    channel: ChannelBrief
    external_order_id: str
    status: OrderStatus
    customer: Customer
    items: list[OrderItemRead]
    total: Decimal
    created_at: datetime
    updated_at: datetime


class StatusChange(CamelModel):
    status: OrderStatus


class CancelRequest(CamelModel):
    reason: str | None = Field(default=None, max_length=255)

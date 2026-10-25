import uuid
from decimal import Decimal

from sqlmodel import Field

from models.enums import OrderStatus
from schemas.base import CamelModel
from schemas.order import Customer


class WebhookItem(CamelModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class WebhookOrder(CamelModel):
    external_order_id: str = Field(min_length=1, max_length=100)
    customer: Customer
    items: list[WebhookItem] = Field(min_length=1)


class WebhookResult(CamelModel):
    order_id: uuid.UUID
    status: OrderStatus

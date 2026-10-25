import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import field_validator
from sqlmodel import Field

from models.enums import MovementType
from schemas.base import CamelModel


class ProductCreate(CamelModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    ean: str | None = Field(default=None, max_length=32)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    initial_stock: int = Field(default=0, ge=0)


class ProductUpdate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    ean: str | None = Field(default=None, max_length=32)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class ProductRead(CamelModel):
    id: uuid.UUID
    sku: str
    name: str
    ean: str | None
    price: Decimal
    stock_quantity: int
    archived: bool
    created_at: datetime
    updated_at: datetime


class StockAdjustment(CamelModel):
    delta: int
    reason: str = Field(min_length=1, max_length=255)

    @field_validator("delta")
    @classmethod
    def delta_not_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("delta nie może być 0")
        return value


class StockMovementRead(CamelModel):
    id: uuid.UUID
    product_id: uuid.UUID
    order_id: uuid.UUID | None
    user_id: uuid.UUID | None
    delta: int
    type: MovementType
    reason: str | None
    created_at: datetime


class StockAdjustmentResult(CamelModel):
    stock_quantity: int
    movement: StockMovementRead

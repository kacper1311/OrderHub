import uuid
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint
from decimal import Decimal


class Product(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock_quantity_non_negative"),
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku: str = Field(unique=True, index=True)
    name: str
    ean: str | None = None
    price: Decimal = Field(max_digits=10, decimal_places=2)
    stock_quantity: int
    archived: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

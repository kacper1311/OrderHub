import uuid
from sqlmodel import SQLModel, Field
from sqlalchemy import CheckConstraint
from decimal import Decimal


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_non_negative"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id")
    product_id: uuid.UUID = Field(foreign_key="products.id")
    quantity: int
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)

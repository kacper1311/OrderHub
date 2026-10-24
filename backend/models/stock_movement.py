import uuid
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from .enums import MovementType


class StockMovement(SQLModel, table=True):
    __tablename__ = "stock_movements"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id")
    order_id: uuid.UUID | None = Field(default=None, foreign_key="orders.id")
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    delta: int
    type: MovementType
    reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

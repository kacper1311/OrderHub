import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, select

from models import Product, StockMovement
from models.enums import MovementType


class InsufficientStockError(Exception):
    def __init__(self, sku: str):
        super().__init__(f"Niewystarczający stan produktu {sku}")
        self.sku = sku


def lock_products(session: Session, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, Product]:
    """SELECT ... FOR UPDATE na produktach.

    Blokada trwa do commit/rollback, więc inne transakcje czekają na te wiersze.
    Stała kolejność (po id) zapobiega zakleszczeniu (deadlock), gdy dwie transakcje
    blokują te same produkty.

    populate_existing: jeśli produkt był już wczytany w tej sesji (np. wyszukanie po SKU),
    SQLAlchemy domyślnie zostawiłby stary obiekt ze starym stanem. Po odczekaniu na blokadę
    musimy widzieć stan aktualny – inaczej dwie transakcje sprzedadzą tę samą sztukę.
    """
    statement = (
        select(Product)
        .where(col(Product.id).in_(set(product_ids)))
        .order_by(Product.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {product.id: product for product in session.exec(statement).all()}


def change_stock(
    session: Session,
    product: Product,
    delta: int,
    movement_type: MovementType,
    *,
    order_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> StockMovement:
    """Jedyne miejsce w aplikacji, które zmienia stan magazynowy.

    Zawsze zapisuje ruch w stock_movements. Produkt musi być wcześniej zablokowany
    (lock_products). Nie robi commit – robi go wywołujący, żeby całość była
    jedną transakcją.
    """
    new_quantity = product.stock_quantity + delta
    if new_quantity < 0:
        raise InsufficientStockError(product.sku)

    product.stock_quantity = new_quantity
    product.updated_at = datetime.now(timezone.utc)
    movement = StockMovement(
        product_id=product.id,
        order_id=order_id,
        user_id=user_id,
        delta=delta,
        type=movement_type,
        reason=reason,
    )
    session.add(product)
    session.add(movement)
    return movement

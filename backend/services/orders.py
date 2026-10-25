import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import Order, OrderItem
from models.enums import MovementType, OrderStatus
from services.stock import InsufficientStockError, change_stock, lock_products

# Dozwolone przejścia statusów (diagram stanów z Etapu I)
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.NOWE: {OrderStatus.W_REALIZACJI, OrderStatus.ANULOWANE},
    OrderStatus.W_REALIZACJI: {OrderStatus.WYSLANE, OrderStatus.ANULOWANE},
    OrderStatus.WSTRZYMANE: {OrderStatus.NOWE, OrderStatus.ANULOWANE},
    OrderStatus.WYSLANE: set(),
    OrderStatus.ANULOWANE: set(),
}

# Statusy, w których towar jest zarezerwowany (stan został zmniejszony)
RESERVED_STATUSES = {OrderStatus.NOWE, OrderStatus.W_REALIZACJI}


class DuplicateOrderError(Exception):
    pass


class OrderNotFoundError(Exception):
    pass


class InvalidTransitionError(Exception):
    def __init__(self, current: OrderStatus, target: OrderStatus):
        super().__init__(f"Niedozwolone przejście statusu {current.value} -> {target.value}")


@dataclass
class ItemRequest:
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal


def _quantities_per_product(items) -> dict[uuid.UUID, int]:
    # Ten sam produkt może wystąpić w kilku pozycjach – sumujemy ilości
    needed: dict[uuid.UUID, int] = defaultdict(int)
    for item in items:
        needed[item.product_id] += item.quantity
    return needed


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_order(
    session: Session,
    *,
    channel_id: uuid.UUID,
    external_order_id: str,
    customer_name: str,
    customer_email: str,
    shipping_address: str,
    items: list[ItemRequest],
    hold_if_insufficient: bool = True,
) -> Order:
    """Zapis zamówienia i rezerwacja stanu w jednej transakcji.

    Używane przez webhook (brak stanu -> WSTRZYMANE) i ręczne dodanie
    (hold_if_insufficient=False -> InsufficientStockError, nic nie zapisujemy).
    """
    duplicate = session.exec(
        select(Order).where(Order.channel_id == channel_id, Order.external_order_id == external_order_id)
    ).first()
    if duplicate:
        raise DuplicateOrderError()

    needed = _quantities_per_product(items)

    # SELECT ... FOR UPDATE: od tej chwili do commit nikt inny nie zmieni tych produktów.
    # Druga transakcja zamawiająca ten sam produkt czeka tutaj i zobaczy już zmniejszony stan.
    products = lock_products(session, list(needed))

    enough = all(products[pid].stock_quantity >= qty for pid, qty in needed.items())
    if not enough and not hold_if_insufficient:
        missing = next(products[pid] for pid, qty in needed.items() if products[pid].stock_quantity < qty)
        session.rollback()
        raise InsufficientStockError(missing.sku)

    order = Order(
        channel_id=channel_id,
        external_order_id=external_order_id,
        status=OrderStatus.NOWE if enough else OrderStatus.WSTRZYMANE,
        customer_name=customer_name,
        customer_email=customer_email,
        shipping_address=shipping_address,
        total=sum((item.unit_price * item.quantity for item in items), Decimal("0")),
    )
    session.add(order)

    try:
        # flush: INSERT zamówienia teraz, żeby pozycje i ruchy mogły się do niego odwołać (FK)
        session.flush()
        for item in items:
            session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            ))
        if enough:
            for pid, qty in needed.items():
                change_stock(session, products[pid], -qty, MovementType.ORDER, order_id=order.id)
        session.commit()
    except IntegrityError:
        # Równoległy duplikat, który przeszedł sprawdzenie wyżej – złapał go UNIQUE w bazie
        session.rollback()
        raise DuplicateOrderError()

    session.refresh(order)
    return order


def _order_items(session: Session, order_id: uuid.UUID) -> list[OrderItem]:
    return list(session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all())


def _reserve_stock(session: Session, order: Order) -> None:
    """WSTRZYMANE -> NOWE: ponowna próba rezerwacji. Brak stanu -> InsufficientStockError."""
    needed = _quantities_per_product(_order_items(session, order.id))
    products = lock_products(session, list(needed))
    for pid, qty in needed.items():
        if products[pid].stock_quantity < qty:
            raise InsufficientStockError(products[pid].sku)
    for pid, qty in needed.items():
        change_stock(session, products[pid], -qty, MovementType.ORDER, order_id=order.id)


def _return_stock(session: Session, order: Order, reason: str | None) -> None:
    needed = _quantities_per_product(_order_items(session, order.id))
    products = lock_products(session, list(needed))
    for pid, qty in needed.items():
        change_stock(session, products[pid], qty, MovementType.CANCEL, order_id=order.id, reason=reason)


def change_status(
    session: Session,
    order_id: uuid.UUID,
    target: OrderStatus,
    reason: str | None = None,
) -> Order:
    # Blokujemy też samo zamówienie: dwa równoległe anulowania nie zwrócą stanu dwa razy
    order = session.exec(
        select(Order).where(Order.id == order_id).with_for_update().execution_options(populate_existing=True)
    ).first()
    if not order:
        raise OrderNotFoundError()

    if target not in ALLOWED_TRANSITIONS[order.status]:
        session.rollback()
        raise InvalidTransitionError(order.status, target)

    try:
        if target == OrderStatus.ANULOWANE and order.status in RESERVED_STATUSES:
            _return_stock(session, order, reason)
        elif order.status == OrderStatus.WSTRZYMANE and target == OrderStatus.NOWE:
            _reserve_stock(session, order)
    except InsufficientStockError:
        session.rollback()
        raise

    order.status = target
    order.updated_at = _now()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def cancel_order(session: Session, order_id: uuid.UUID, reason: str | None = None) -> Order:
    return change_status(session, order_id, OrderStatus.ANULOWANE, reason)

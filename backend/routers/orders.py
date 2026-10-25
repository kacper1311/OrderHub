import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from database import get_session
from dependencies import Pagination, get_current_user
from models import Channel, Order, OrderItem, Product
from models.enums import OrderStatus
from schemas.order import (
    CancelRequest,
    ChannelBrief,
    Customer,
    OrderCreate,
    OrderDetail,
    OrderItemRead,
    OrderListItem,
    StatusChange,
)
from services.orders import (
    DuplicateOrderError,
    InvalidTransitionError,
    ItemRequest,
    OrderNotFoundError,
    cancel_order,
    change_status,
    create_order,
)
from services.stock import InsufficientStockError

router = APIRouter(prefix="/api/v1/orders", tags=["orders"], dependencies=[Depends(get_current_user)])


def build_order_detail(session: Session, order: Order) -> OrderDetail:
    channel = session.get(Channel, order.channel_id)
    rows = session.exec(
        select(OrderItem, Product)
        .join(Product, OrderItem.product_id == Product.id)
        .where(OrderItem.order_id == order.id)
        .order_by(Product.name)
    ).all()
    return OrderDetail(
        id=order.id,
        channel=ChannelBrief.model_validate(channel),
        external_order_id=order.external_order_id,
        status=order.status,
        customer=Customer(name=order.customer_name, email=order.customer_email, address=order.shipping_address),
        items=[
            OrderItemRead(
                id=item.id,
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item, product in rows
        ],
        total=order.total,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("", response_model=list[OrderListItem])
def list_orders(
    status: OrderStatus | None = None,
    channel_id: uuid.UUID | None = Query(None, alias="channelId"),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    pagination: Pagination = Depends(),
    session: Session = Depends(get_session),
):
    statement = select(Order, Channel).join(Channel, Order.channel_id == Channel.id)
    if status:
        statement = statement.where(Order.status == status)
    if channel_id:
        statement = statement.where(Order.channel_id == channel_id)
    if date_from:
        statement = statement.where(Order.created_at >= date_from)
    if date_to:
        statement = statement.where(Order.created_at <= date_to)
    statement = statement.order_by(col(Order.created_at).desc()).offset(pagination.offset).limit(pagination.limit)

    return [
        OrderListItem(
            id=order.id,
            channel=ChannelBrief.model_validate(channel),
            external_order_id=order.external_order_id,
            status=order.status,
            total=order.total,
            created_at=order.created_at,
        )
        for order, channel in session.exec(statement).all()
    ]


@router.post("", response_model=OrderDetail, status_code=201)
def create_manual_order(data: OrderCreate, session: Session = Depends(get_session)):
    channel = session.get(Channel, data.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Nie znaleziono kanału")

    product_ids = {item.product_id for item in data.items}
    products = {
        p.id: p
        for p in session.exec(
            select(Product).where(col(Product.id).in_(product_ids), Product.archived == False)  # noqa: E712
        ).all()
    }
    missing = product_ids - products.keys()
    if missing:
        raise HTTPException(status_code=422, detail=f"Nieznane produkty: {', '.join(map(str, missing))}")

    try:
        order = create_order(
            session,
            channel_id=channel.id,
            external_order_id=f"MANUAL-{uuid.uuid4().hex[:12].upper()}",
            customer_name=data.customer.name,
            customer_email=data.customer.email,
            shipping_address=data.customer.address,
            items=[
                ItemRequest(product_id=i.product_id, quantity=i.quantity, unit_price=products[i.product_id].price)
                for i in data.items
            ],
            hold_if_insufficient=False,
        )
    except InsufficientStockError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except DuplicateOrderError:
        raise HTTPException(status_code=409, detail="Duplikat zamówienia")
    return build_order_detail(session, order)


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(order_id: uuid.UUID, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Nie znaleziono zamówienia")
    return build_order_detail(session, order)


def _run_status_change(session: Session, action) -> OrderDetail:
    # Wspólna obsługa błędów dla PATCH /status i POST /cancel
    try:
        order = action()
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Nie znaleziono zamówienia")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return build_order_detail(session, order)


@router.patch("/{order_id}/status", response_model=OrderDetail)
def update_status(order_id: uuid.UUID, data: StatusChange, session: Session = Depends(get_session)):
    return _run_status_change(session, lambda: change_status(session, order_id, data.status))


@router.post("/{order_id}/cancel", response_model=OrderDetail)
def cancel(
    order_id: uuid.UUID,
    data: CancelRequest | None = Body(None),
    session: Session = Depends(get_session),
):
    reason = data.reason if data else None
    return _run_status_change(session, lambda: cancel_order(session, order_id, reason))

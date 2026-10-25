import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, col, select

from database import get_session
from models import Channel, Product
from schemas.webhook import WebhookOrder, WebhookResult
from services.orders import DuplicateOrderError, ItemRequest, create_order

# Bez JWT – kanał uwierzytelnia się sekretem w nagłówku
router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/{channel_code}", response_model=WebhookResult, status_code=201)
def receive_order(
    channel_code: str,
    data: WebhookOrder,
    x_webhook_secret: str | None = Header(None, alias="X-Webhook-Secret"),
    session: Session = Depends(get_session),
):
    channel = session.exec(select(Channel).where(Channel.code == channel_code)).first()
    if not channel or not channel.active:
        raise HTTPException(status_code=404, detail="Nieznany kanał")

    # compare_digest porównuje w stałym czasie – czas odpowiedzi nie zdradza, ile znaków się zgadza
    if not x_webhook_secret or not secrets.compare_digest(x_webhook_secret, channel.webhook_secret):
        raise HTTPException(status_code=401, detail="Nieprawidłowy sekret webhooka")

    skus = {item.sku for item in data.items}
    products = {
        p.sku: p
        for p in session.exec(
            select(Product).where(col(Product.sku).in_(skus), Product.archived == False)  # noqa: E712
        ).all()
    }
    unknown = skus - products.keys()
    if unknown:
        raise HTTPException(status_code=422, detail=f"Nieznane SKU: {', '.join(sorted(unknown))}")

    try:
        order = create_order(
            session,
            channel_id=channel.id,
            external_order_id=data.external_order_id,
            customer_name=data.customer.name,
            customer_email=data.customer.email,
            shipping_address=data.customer.address,
            items=[
                ItemRequest(product_id=products[i.sku].id, quantity=i.quantity, unit_price=i.unit_price)
                for i in data.items
            ],
        )
    except DuplicateOrderError:
        raise HTTPException(status_code=409, detail="Zamówienie o tym externalOrderId już istnieje")

    return WebhookResult(order_id=order.id, status=order.status)

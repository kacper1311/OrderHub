import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, or_, select

from database import get_session
from dependencies import Pagination, get_current_user
from models import Product, StockMovement, User
from models.enums import MovementType
from schemas.product import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    StockAdjustment,
    StockAdjustmentResult,
    StockMovementRead,
)
from services.stock import InsufficientStockError, change_stock, lock_products

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_or_404(session: Session, product_id: uuid.UUID) -> Product:
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Nie znaleziono produktu")
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    search: str | None = None,
    pagination: Pagination = Depends(),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    statement = select(Product).where(Product.archived == False)  # noqa: E712
    if search:
        pattern = f"%{search}%"
        statement = statement.where(or_(col(Product.sku).ilike(pattern), col(Product.name).ilike(pattern)))
    statement = statement.order_by(Product.name).offset(pagination.offset).limit(pagination.limit)
    return session.exec(statement).all()


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    data: ProductCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if session.exec(select(Product).where(Product.sku == data.sku)).first():
        raise HTTPException(status_code=409, detail="Produkt o tym SKU już istnieje")

    product = Product(
        sku=data.sku,
        name=data.name,
        ean=data.ean,
        price=data.price,
        stock_quantity=0,
    )
    session.add(product)
    try:
        # flush wysyła INSERT produktu (bez commit), żeby ruch mógł się do niego odwołać
        session.flush()
        if data.initial_stock > 0:
            change_stock(
                session, product, data.initial_stock, MovementType.MANUAL,
                user_id=user.id, reason="Stan początkowy",
            )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Produkt o tym SKU już istnieje")
    session.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return get_product_or_404(session, product_id)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    product = get_product_or_404(session, product_id)
    product.name = data.name
    product.ean = data.ean
    product.price = data.price
    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def archive_product(
    product_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    # Nie usuwamy – produkt może mieć zamówienia i historię ruchów
    product = get_product_or_404(session, product_id)
    product.archived = True
    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    session.commit()
    return Response(status_code=204)


@router.post("/{product_id}/stock-adjustments", response_model=StockAdjustmentResult)
def adjust_stock(
    product_id: uuid.UUID,
    data: StockAdjustment,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Blokada wiersza: równoległe zamówienie poczeka, aż skończymy korektę
    product = lock_products(session, [product_id]).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Nie znaleziono produktu")

    try:
        movement = change_stock(
            session, product, data.delta, MovementType.MANUAL,
            user_id=user.id, reason=data.reason,
        )
    except InsufficientStockError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Stan magazynowy spadłby poniżej zera")

    session.commit()
    session.refresh(product)
    session.refresh(movement)
    return StockAdjustmentResult(
        stock_quantity=product.stock_quantity,
        movement=StockMovementRead.model_validate(movement),
    )


@router.get("/{product_id}/stock-movements", response_model=list[StockMovementRead])
def list_stock_movements(
    product_id: uuid.UUID,
    pagination: Pagination = Depends(),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    get_product_or_404(session, product_id)
    statement = (
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(col(StockMovement.created_at).desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    return session.exec(statement).all()

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from database import get_session
from dependencies import get_current_user
from models import Product
from schemas.product import ProductRead

router = APIRouter(prefix="/api/v1/stock", tags=["stock"], dependencies=[Depends(get_current_user)])


@router.get("/low", response_model=list[ProductRead])
def low_stock(threshold: int = Query(5, ge=0), session: Session = Depends(get_session)):
    statement = (
        select(Product)
        .where(Product.archived == False, Product.stock_quantity < threshold)  # noqa: E712
        .order_by(Product.stock_quantity, Product.name)
    )
    return session.exec(statement).all()

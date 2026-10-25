from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import User
from schemas.auth import LoginRequest, LoginResponse
from schemas.user import UserRead
from services.security import verify_password, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()

    # Jeden komunikat dla wszystkich przypadków – nie zdradzamy, czy konto istnieje
    if not user or not verify_password(data.password, user.password_hash) or not user.active:
        raise HTTPException(status_code=401, detail="Nieprawidłowy email lub hasło")

    token = create_access_token(user.id, user.role)
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))

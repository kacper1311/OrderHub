import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database import get_session
from dependencies import require_admin
from models import User
from schemas.user import UserCreate, UserRead, UserUpdate
from services.security import hash_password

# dependencies na routerze: każdy endpoint w tym pliku wymaga roli ADMIN
router = APIRouter(prefix="/api/v1/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserRead])
def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User).order_by(User.email)).all()


@router.post("", response_model=UserRead, status_code=201)
def create_user(data: UserCreate, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == data.email)).first():
        raise HTTPException(status_code=409, detail="Email jest już zajęty")

    user = User(
        email=data.email,
        name=data.name,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        # Dwa równoległe żądania z tym samym emailem – UNIQUE w bazie łapie drugie
        session.rollback()
        raise HTTPException(status_code=409, detail="Email jest już zajęty")
    session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")

    # Admin nie może sam sobie odebrać dostępu – inaczej system mógłby zostać bez admina
    if user.id == current_admin.id and (
        data.active is False or (data.role is not None and data.role != current_admin.role)
    ):
        raise HTTPException(status_code=400, detail="Nie możesz dezaktywować ani zmienić roli własnego konta")

    # exclude_unset: tylko pola, które klient faktycznie wysłał; exclude_none: pomijamy jawne null
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    password = changes.pop("password", None)
    for field, value in changes.items():
        setattr(user, field, value)
    if password:
        user.password_hash = hash_password(password)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

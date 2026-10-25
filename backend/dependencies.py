import uuid

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from database import get_session
from models import User
from models.enums import UserRole
from services.security import decode_access_token

# auto_error=False: brak nagłówka obsługujemy sami, żeby zawsze zwracać 401
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Brak lub nieprawidłowy token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized

    # Sprawdzamy bazę przy każdym żądaniu: dezaktywowane konto traci dostęp od razu
    user = session.get(User, user_id)
    if not user or not user.active:
        raise unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Wymagana rola ADMIN")
    return user


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
    ):
        self.limit = limit
        self.offset = (page - 1) * limit

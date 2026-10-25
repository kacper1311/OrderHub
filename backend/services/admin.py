import os

from dotenv import load_dotenv
from sqlmodel import Session, select

from database import engine
from models import User
from models.enums import UserRole
from services.security import hash_password

load_dotenv()


def create_admin_if_missing() -> None:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    name = os.getenv("ADMIN_NAME")
    if not email or not password or not name:
        raise RuntimeError("Brak ADMIN_EMAIL, ADMIN_PASSWORD lub ADMIN_NAME w pliku .env")

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            return

        admin = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=UserRole.ADMIN,
        )
        session.add(admin)
        session.commit()

import uuid
from sqlmodel import SQLModel, Field
from .enums import UserRole


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    role: UserRole
    active: bool = Field(default=True)

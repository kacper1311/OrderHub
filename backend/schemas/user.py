import uuid
from sqlmodel import SQLModel, Field
from models.enums import UserRole


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    active: bool


class UserCreate(SQLModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    role: UserRole


class UserUpdate(SQLModel):
    # Wszystkie pola opcjonalne: PATCH zmienia tylko to, co przyszło
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8)

import uuid
from sqlmodel import SQLModel
from models.enums import UserRole


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    active: bool

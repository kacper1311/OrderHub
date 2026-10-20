import uuid
from sqlmodel import SQLModel, Field


class Channel(SQLModel, table=True):
    __tablename__ = "channels"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    webhook_secret: str
    active: bool = Field(default=True)

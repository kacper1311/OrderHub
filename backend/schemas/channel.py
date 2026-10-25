import re
import uuid

from pydantic import field_validator
from sqlmodel import Field

from schemas.base import CamelModel


class ChannelCreate(CamelModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    webhook_secret: str = Field(min_length=16, max_length=255)

    @field_validator("code")
    @classmethod
    def code_url_safe(cls, value: str) -> str:
        # code trafia do adresu webhooka, więc tylko małe litery, cyfry i myślniki
        if not re.fullmatch(r"[a-z0-9-]+", value):
            raise ValueError("code może zawierać tylko małe litery, cyfry i myślniki")
        return value


class ChannelUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    webhook_secret: str | None = Field(default=None, min_length=16, max_length=255)
    active: bool | None = None


class ChannelRead(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    active: bool


class ChannelAdminRead(ChannelRead):
    # Sekret widzi tylko ADMIN
    webhook_secret: str

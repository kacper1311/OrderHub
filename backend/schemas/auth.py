from sqlmodel import SQLModel, Field
from .user import UserRead


class LoginRequest(SQLModel):
    email: str
    password: str


class LoginResponse(SQLModel):
    access_token: str = Field(serialization_alias="accessToken")
    user: UserRead
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.user import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    avatar: str | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar: str | None = None

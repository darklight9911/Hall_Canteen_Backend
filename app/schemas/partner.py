import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.partner_application import ApplicationStatus


class PartnerApplyRequest(BaseModel):
    id_token: str
    phone: str = Field(min_length=3, max_length=32)
    full_name: str = Field(min_length=1, max_length=255)
    shop_name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=512)
    photo: str = Field(min_length=1)  # base64 data URL


class PartnerApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    phone: str
    full_name: str
    shop_name: str
    location: str
    photo: str
    status: ApplicationStatus
    created_at: datetime
    reviewed_at: datetime | None


class RestaurantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    location: str
    photo: str | None


class FoodItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    price: int = Field(ge=0)
    category: str = Field(default="", max_length=100)
    image: str | None = None
    is_available: bool = True


class FoodItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    image: str | None = None
    is_available: bool | None = None


class FoodItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    price: int
    category: str
    image: str | None
    is_available: bool

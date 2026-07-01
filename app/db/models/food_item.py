import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.delivery_slot import DeliverySlot

# Junction table — no model class needed.
food_item_slots = Table(
    "food_item_slots",
    Base.metadata,
    Column("food_item_id", UUID(as_uuid=True), ForeignKey("food_items.id", ondelete="CASCADE"), primary_key=True),
    Column("slot_id", UUID(as_uuid=True), ForeignKey("delivery_slots.id", ondelete="CASCADE"), primary_key=True),
)


class FoodItem(Base):
    """A food item listed by a partner under their restaurant."""

    __tablename__ = "food_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    slots: Mapped[list["DeliverySlot"]] = relationship(
        "DeliverySlot", secondary=food_item_slots, lazy="selectin"
    )

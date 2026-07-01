"""food_item_slots junction table

Revision ID: 0006_food_item_slots
Revises: 0005_delivery_slots
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_food_item_slots"
down_revision: str | None = "0005_delivery_slots"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "food_item_slots",
        sa.Column(
            "food_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("food_items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_slots.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("food_item_slots")

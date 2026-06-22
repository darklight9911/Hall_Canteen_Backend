"""partner applications, restaurants, food items

Revision ID: 0003_partner_tables
Revises: 0002_rename_roles
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_partner_tables"
down_revision: str | None = "0002_rename_roles"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

application_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="application_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    sa.Enum("pending", "approved", "rejected", name="application_status").create(
        bind, checkfirst=True
    )

    op.create_table(
        "partner_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("shop_name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=False),
        sa.Column("photo", sa.Text(), nullable=False),
        sa.Column("status", application_status, nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_partner_applications_user_id", "partner_applications", ["user_id"])

    op.create_table(
        "restaurants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=False),
        sa.Column("photo", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_restaurants_owner_id", "restaurants", ["owner_id"], unique=True)

    op.create_table(
        "food_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_food_items_restaurant_id", "food_items", ["restaurant_id"])


def downgrade() -> None:
    op.drop_index("ix_food_items_restaurant_id", table_name="food_items")
    op.drop_table("food_items")
    op.drop_index("ix_restaurants_owner_id", table_name="restaurants")
    op.drop_table("restaurants")
    op.drop_index("ix_partner_applications_user_id", table_name="partner_applications")
    op.drop_table("partner_applications")
    sa.Enum(name="application_status").drop(op.get_bind(), checkfirst=True)

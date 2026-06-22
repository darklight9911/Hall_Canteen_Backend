"""rename roles: admin -> developer, staff -> partner

Revision ID: 0002_rename_roles
Revises: 0001_create_users
Create Date: 2026-06-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_rename_roles"
down_revision: str | None = "0001_create_users"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Renaming an enum value preserves existing rows (same underlying value).
    op.execute("ALTER TYPE user_role RENAME VALUE 'admin' TO 'developer'")
    op.execute("ALTER TYPE user_role RENAME VALUE 'staff' TO 'partner'")


def downgrade() -> None:
    op.execute("ALTER TYPE user_role RENAME VALUE 'developer' TO 'admin'")
    op.execute("ALTER TYPE user_role RENAME VALUE 'partner' TO 'staff'")

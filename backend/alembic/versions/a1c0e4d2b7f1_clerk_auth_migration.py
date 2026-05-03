"""clerk auth migration

Replaces argon2 password auth with Clerk JWT identity mapping.

Schema changes on app.users:
  - add clerk_user_id TEXT UNIQUE NULLABLE
  - drop hashed_password

Dev operators MUST run `TRUNCATE app.users CASCADE;` before upgrading, since
hashed_password is NOT NULL today and any existing rows would block the drop.
There is no attempt to preserve legacy accounts — Clerk owns identity now.

Revision ID: a1c0e4d2b7f1
Revises: 21c03da60f49
Create Date: 2026-04-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c0e4d2b7f1"
down_revision: Union[str, Sequence[str], None] = "21c03da60f49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("clerk_user_id", sa.Text(), nullable=True),
        schema="app",
    )
    op.create_unique_constraint(
        "uq_users_clerk_user_id",
        "users",
        ["clerk_user_id"],
        schema="app",
    )
    op.drop_column("users", "hashed_password", schema="app")


def downgrade() -> None:
    # Recreate hashed_password as nullable so rollback does not require
    # repopulating credentials for any Clerk-created rows.
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.Text(), nullable=True),
        schema="app",
    )
    op.drop_constraint(
        "uq_users_clerk_user_id",
        "users",
        schema="app",
        type_="unique",
    )
    op.drop_column("users", "clerk_user_id", schema="app")

"""Ensure earned credits exist on older usage snapshot tables.

Revision ID: 0002_earned_credits
Revises: 0001_initial
"""

from alembic import op

revision = "0002_earned_credits"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE usage_snapshots ADD COLUMN IF NOT EXISTS "
        "earned_credits FLOAT NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.drop_column("usage_snapshots", "earned_credits")

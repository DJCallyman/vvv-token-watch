"""Create the current application schema.

Revision ID: 0001_initial
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("diem", sa.Float(), nullable=False),
        sa.Column("usd", sa.Float(), nullable=False),
        sa.Column("bundled_credits", sa.Float(), nullable=False),
        sa.Column("earned_credits", sa.Float(), nullable=False),
        sa.Column("epoch_start", sa.String(length=64), nullable=True),
        sa.Column("next_epoch", sa.String(length=64), nullable=True),
        sa.Column("target_date", sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_snapshots_timestamp", "usage_snapshots", ["timestamp"])
    op.create_index("ix_usage_snapshots_scope_ts", "usage_snapshots", ["scope", "timestamp"])

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("token_id", sa.String(length=64), nullable=False),
        sa.Column("price_usd", sa.Float(), nullable=True),
        sa.Column("price_aud", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("change_24h", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_snapshots_timestamp", "price_snapshots", ["timestamp"])
    op.create_index("ix_price_snapshots_token_ts", "price_snapshots", ["token_id", "timestamp"])

    op.create_table(
        "alert_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("comparison", sa.String(length=8), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_config_id", sa.Integer(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["alert_config_id"], ["alert_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_events_triggered_at", "alert_events", ["triggered_at"])
    op.create_index("ix_alert_events_ack_ts", "alert_events", ["acknowledged", "triggered_at"])

    op.create_table(
        "billing_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entry_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sku", sa.String(length=256), nullable=False),
        sa.Column("units", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("price_per_unit_usd", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("inference_execution_time", sa.Integer(), nullable=True),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entry_timestamp", "sku", "request_id",
            name="uq_billing_entry_natural_key",
        ),
    )
    op.create_index("ix_billing_entries_entry_timestamp", "billing_entries", ["entry_timestamp"])
    op.create_index("ix_billing_entries_ts", "billing_entries", ["entry_timestamp"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("values", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_billing_entries_ts", table_name="billing_entries")
    op.drop_index("ix_billing_entries_entry_timestamp", table_name="billing_entries")
    op.drop_table("billing_entries")
    op.drop_index("ix_alert_events_ack_ts", table_name="alert_events")
    op.drop_index("ix_alert_events_triggered_at", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_table("alert_configs")
    op.drop_index("ix_price_snapshots_token_ts", table_name="price_snapshots")
    op.drop_index("ix_price_snapshots_timestamp", table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_index("ix_usage_snapshots_scope_ts", table_name="usage_snapshots")
    op.drop_index("ix_usage_snapshots_timestamp", table_name="usage_snapshots")
    op.drop_table("usage_snapshots")

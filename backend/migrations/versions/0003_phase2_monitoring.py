"""Phase 2 schema: alert signals, notifications, watchlists, wallet auth, signals.

Revision ID: 0003_phase2_monitoring
Revises: 0002_earned_credits
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_phase2_monitoring"
down_revision = "0002_earned_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    op.execute(
        "ALTER TABLE alert_configs ADD COLUMN IF NOT EXISTS window_seconds INTEGER"
    )
    op.execute(
        "ALTER TABLE alert_configs ADD COLUMN IF NOT EXISTS min_samples INTEGER"
    )

    if "notification_channels" not in existing_tables:
        op.create_table(
            "notification_channels",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("config", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "notification_deliveries" not in existing_tables:
        op.create_table(
            "notification_deliveries",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("alert_event_id", sa.Integer(), nullable=False),
            sa.Column("channel_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dedupe_key", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["alert_event_id"], ["alert_events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["channel_id"], ["notification_channels.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dedupe_key", name="uq_notification_delivery_dedupe"),
        )
        op.create_index(
            "ix_notification_deliveries_alert_event_id",
            "notification_deliveries",
            ["alert_event_id"],
        )
        op.create_index(
            "ix_notification_deliveries_channel_id",
            "notification_deliveries",
            ["channel_id"],
        )
        op.create_index(
            "ix_notification_deliveries_status_next",
            "notification_deliveries",
            ["status", "next_attempt_at"],
        )

    if "watchlist_items" not in existing_tables:
        op.create_table(
            "watchlist_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("chain", sa.String(length=64), nullable=False),
            sa.Column("token", sa.String(length=32), nullable=False),
            sa.Column("address", sa.String(length=42), nullable=False),
            sa.Column("label", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("chain", "address", name="uq_watchlist_chain_address"),
        )

    if "wallet_challenges" not in existing_tables:
        op.create_table(
            "wallet_challenges",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("address", sa.String(length=42), nullable=False),
            sa.Column("chain_id", sa.Integer(), nullable=False),
            sa.Column("nonce", sa.String(length=64), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nonce"),
        )
        op.create_index("ix_wallet_challenges_address", "wallet_challenges", ["address"])

    if "wallet_sessions" not in existing_tables:
        op.create_table(
            "wallet_sessions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("address", sa.String(length=42), nullable=False),
            sa.Column("chain_id", sa.Integer(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_wallet_sessions_address", "wallet_sessions", ["address"])

    if "signal_records" not in existing_tables:
        op.create_table(
            "signal_records",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("subject", sa.String(length=32), nullable=False),
            sa.Column("direction", sa.String(length=16), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("rationale", sa.Text(), nullable=False),
            sa.Column("sources", sa.Text(), nullable=False),
            sa.Column("metrics", sa.Text(), nullable=False),
            sa.Column("entry_price_usd", sa.Float(), nullable=True),
            sa.Column("outcome_status", sa.String(length=16), nullable=False),
            sa.Column("outcome_value_usd", sa.Float(), nullable=True),
            sa.Column("outcome_note", sa.Text(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_signal_records_created", "signal_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_signal_records_created", table_name="signal_records")
    op.drop_table("signal_records")

    op.drop_index("ix_wallet_sessions_address", table_name="wallet_sessions")
    op.drop_table("wallet_sessions")

    op.drop_index("ix_wallet_challenges_address", table_name="wallet_challenges")
    op.drop_table("wallet_challenges")

    op.drop_table("watchlist_items")

    op.drop_index(
        "ix_notification_deliveries_status_next",
        table_name="notification_deliveries",
    )
    op.drop_index(
        "ix_notification_deliveries_channel_id", table_name="notification_deliveries"
    )
    op.drop_index(
        "ix_notification_deliveries_alert_event_id",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")
    op.drop_table("notification_channels")

    op.drop_column("alert_configs", "min_samples")
    op.drop_column("alert_configs", "window_seconds")

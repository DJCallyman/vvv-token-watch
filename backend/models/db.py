"""SQLAlchemy ORM models for persistent history, alerts, and benchmark jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UsageSnapshot(Base):
    """Point-in-time usage totals (epoch or daily)."""

    __tablename__ = "usage_snapshots"
    __table_args__ = (
        Index("ix_usage_snapshots_scope_ts", "scope", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # epoch | daily
    diem: Mapped[float] = mapped_column(Float, default=0.0)
    usd: Mapped[float] = mapped_column(Float, default=0.0)
    bundled_credits: Mapped[float] = mapped_column(Float, default=0.0)
    earned_credits: Mapped[float] = mapped_column(Float, default=0.0)
    epoch_start: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    next_epoch: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_date: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)


class PriceSnapshot(Base):
    """Point-in-time token price sample."""

    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("ix_price_snapshots_token_ts", "token_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    token_id: Mapped[str] = mapped_column(String(64), nullable=False)  # vvv | diem
    price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_aud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class AlertConfig(Base):
    """User-defined alert threshold configuration."""

    __tablename__ = "alert_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # usage_percent | balance_threshold | price_threshold | rate_of_change | anomaly
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    # e.g. diem_usage_percent, diem_balance, vvv_price_usd
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    comparison: Mapped[str] = mapped_column(String(8), default="gte")  # gte | lte
    # Signal configuration (Slice 2.2). Only meaningful for rate_of_change and
    # anomaly alert types. NULL preserves legacy threshold behavior.
    window_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_samples: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    events: Mapped[list["AlertEvent"]] = relationship(
        "AlertEvent", back_populates="config", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    """Triggered alert event."""

    __tablename__ = "alert_events"
    __table_args__ = (
        Index("ix_alert_events_ack_ts", "acknowledged", "triggered_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_config_id: Mapped[int] = mapped_column(ForeignKey("alert_configs.id"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    config: Mapped[AlertConfig] = relationship("AlertConfig", back_populates="events")

class BillingEntry(Base):
    """A single Venice billing ledger entry, persisted for fast analytics.

    Billing data is append-only — entries are never modified or deleted
    upstream. By storing them locally we avoid re-walking the full history
    on every analytics request; we only fetch entries newer than the
    newest stored timestamp.
    """

    __tablename__ = "billing_entries"
    __table_args__ = (
        UniqueConstraint("entry_timestamp", "sku", "request_id", name="uq_billing_entry_natural_key"),
        Index("ix_billing_entries_ts", "entry_timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # When the billing event occurred (from the API's "timestamp" field).
    entry_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(256), nullable=False)
    units: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    price_per_unit_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Inference details (nullable — not all entries have them)
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    inference_execution_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # When we stored this entry (for debugging / audit)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AppSettings(Base):
    """Deployment-level user settings that override environment defaults."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    values: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class NotificationChannel(Base):
    """Per-channel notification destination (Slice 2.4).

    ``config`` stores adapter-specific JSON. Secrets (Discord webhook URLs)
    are never returned by the API or written to logs; API responses expose a
    masked URL only.
    """

    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="discord")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class NotificationDelivery(Base):
    """Durable delivery attempt for an alert event (Slice 2.4).

    ``dedupe_key`` is unique so re-evaluating an alert cannot enqueue or send
    the same event to the same channel twice.
    """

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notification_delivery_dedupe"),
        Index("ix_notification_deliveries_status_next", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_event_id: Mapped[int] = mapped_column(
        ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class WatchlistItem(Base):
    """Persisted wallet/address watchlist entry (Slice 2.5)."""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("chain", "address", name="uq_watchlist_chain_address"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain: Mapped[str] = mapped_column(String(64), nullable=False, default="base-mainnet")
    token: Mapped[str] = mapped_column(String(32), nullable=False, default="vvv")
    address: Mapped[str] = mapped_column(String(42), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WalletChallenge(Base):
    """One-time, expiring, chain-bound SIWE-style challenge (Slice 2.8)."""

    __tablename__ = "wallet_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WalletSession(Base):
    """Opaque read-only wallet session, stored as a SHA-256 hash (Slice 2.8)."""

    __tablename__ = "wallet_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SignalRecord(Base):
    """Structured AI signal with confidence and outcome tracking (Phase 3)."""

    __tablename__ = "signal_records"
    __table_args__ = (
        Index("ix_signal_records_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # sentiment | x_sentiment | manual
    subject: Mapped[str] = mapped_column(String(32), nullable=False, default="vvv")
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # bullish | bearish | neutral
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sources: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metrics: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    entry_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    outcome_value_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

# NOTE: A previous incarnation of the project defined a BenchmarkRun ORM model
# here for persisting in-memory benchmark job metadata across restarts. The
# model was never wired to a repository; the actual source of truth for runs
# is the JSON results files written by scripts/benchmark_models.py to
# BENCHMARK_RESULTS_DIR. The model was removed so the schema no longer
# implies a feature that does not exist.

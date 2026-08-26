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
    token_id: Mapped[str] = mapped_column(String(64), nullable=False)  # vvv | diem | coingecko id
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
    # usage_percent | balance_threshold | price_threshold
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    # e.g. diem_usage_percent, diem_balance, vvv_price_usd
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    comparison: Mapped[str] = mapped_column(String(8), default="gte")  # gte | lte
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

# NOTE: A previous incarnation of the project defined a BenchmarkRun ORM model
# here for persisting in-memory benchmark job metadata across restarts. The
# model was never wired to a repository; the actual source of truth for runs
# is the JSON results files written by scripts/benchmark_models.py to
# BENCHMARK_RESULTS_DIR. The model was removed so the schema no longer
# implies a feature that does not exist.

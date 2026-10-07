"""Tests for Slice 2.4 durable notification delivery (Discord adapter)."""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.models.db import AlertConfig, AlertEvent
from backend.services import notification_service as ns


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def _make_event(session, message="vvv spike") -> AlertEvent:
    cfg = AlertConfig(
        name="test",
        alert_type="price_threshold",
        metric="vvv_price_usd",
        threshold=1.0,
        comparison="gte",
        enabled=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    event = AlertEvent(alert_config_id=cfg.id, message=message, value=1.0)
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


def _fake_response(status_code=204, headers=None) -> httpx.Response:
    return httpx.Response(
        status_code,
        request=httpx.Request("POST", "https://discord.com/api/webhooks/1/token"),
        headers=headers or {},
    )


# ---------------------------------------------------------------------------
# URL validation and masking
# ---------------------------------------------------------------------------


def test_discord_webhook_accepts_only_allowlisted_hosts():
    url = "https://discord.com/api/webhooks/123456/abcdef"
    assert ns.validate_discord_webhook(url) == url
    for bad in (
        "http://discord.com/api/webhooks/123/abc",
        "https://evil.example.com/api/webhooks/123/abc",
        "https://discord.com.evil.example/api/webhooks/123/abc",
        "https://discord.com/not-webhooks/123/abc",
        "https://user:pass@discord.com/api/webhooks/123/abc",
        "",
    ):
        with pytest.raises(ns.ChannelValidationError):
            ns.validate_discord_webhook(bad)


def test_mask_webhook_url_hides_token():
    masked = ns.mask_webhook_url("https://discord.com/api/webhooks/999/secrettoken")
    assert "secrettoken" not in masked
    assert "999" in masked


@pytest.mark.asyncio
async def test_channel_public_dict_masks_secret(session):
    channel = await ns.create_channel(
        session,
        name="ops",
        webhook_url="https://discord.com/api/webhooks/42/topsecret",
    )
    public = ns.channel_public_dict(channel)
    assert "topsecret" not in json.dumps(public)
    assert public["webhook_url_masked"].endswith("****")
    assert "config" not in public


@pytest.mark.asyncio
async def test_create_channel_rejects_foreign_host(session):
    with pytest.raises(ns.ChannelValidationError):
        await ns.create_channel(
            session, name="bad", webhook_url="https://example.com/api/webhooks/1/x"
        )


# ---------------------------------------------------------------------------
# Delivery durability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enqueue_is_deduplicated_per_event_and_channel(session):
    channel = await ns.create_channel(
        session, name="ops", webhook_url="https://discord.com/api/webhooks/7/token"
    )
    event = await _make_event(session)
    first = await ns.enqueue_for_events(session, [event])
    second = await ns.enqueue_for_events(session, [event])
    assert len(first) == 1
    assert second == []
    rows = await ns.list_deliveries(session)
    assert len(rows) == 1
    assert rows[0][0].channel_id == channel.id


@pytest.mark.asyncio
async def test_dispatch_success_marks_sent(session, monkeypatch):
    await ns.create_channel(
        session, name="ops", webhook_url="https://discord.com/api/webhooks/7/token"
    )
    event = await _make_event(session, "DIEM low")

    async def fake_post(url, content):
        assert "DIEM low" in content
        return _fake_response(204)

    monkeypatch.setattr(ns, "_post_discord", fake_post)
    await ns.deliver_events(session, [event])
    rows = await ns.list_deliveries(session)
    assert rows[0][0].status == "sent"
    assert rows[0][0].attempts == 1
    assert rows[0][0].last_error is None


@pytest.mark.asyncio
async def test_dispatch_retries_then_fails_bounded(session, monkeypatch):
    await ns.create_channel(
        session, name="ops", webhook_url="https://discord.com/api/webhooks/7/token"
    )
    event = await _make_event(session)

    async def failing_post(url, content):
        return _fake_response(500)

    monkeypatch.setattr(ns, "_post_discord", failing_post)
    monkeypatch.setattr(ns, "RETRY_BACKOFF_SECONDS", 0)
    await ns.enqueue_for_events(session, [event])
    for _ in range(ns.MAX_DELIVERY_ATTEMPTS):
        await ns.dispatch_pending(session)
    rows = await ns.list_deliveries(session)
    delivery = rows[0][0]
    assert delivery.status == "failed"
    assert delivery.attempts == ns.MAX_DELIVERY_ATTEMPTS
    assert "HTTP 500" in (delivery.last_error or "")

    # Bounded retries: further dispatch attempts do nothing.
    attempted = await ns.dispatch_pending(session)
    assert attempted == []


@pytest.mark.asyncio
async def test_rate_limited_uses_retry_after(session, monkeypatch):
    await ns.create_channel(
        session, name="ops", webhook_url="https://discord.com/api/webhooks/7/token"
    )
    event = await _make_event(session)

    async def limited_post(url, content):
        return _fake_response(429, headers={"retry-after": "120"})

    monkeypatch.setattr(ns, "_post_discord", limited_post)
    await ns.enqueue_for_events(session, [event])
    await ns.dispatch_pending(session)
    rows = await ns.list_deliveries(session)
    delivery = rows[0][0]
    assert delivery.status == "pending"
    next_attempt = delivery.next_attempt_at
    if next_attempt.tzinfo is None:
        next_attempt = next_attempt.replace(tzinfo=timezone.utc)
    delta = (next_attempt - datetime.now(timezone.utc)).total_seconds()
    assert 100 < delta <= 130


@pytest.mark.asyncio
async def test_network_error_stores_no_url(session, monkeypatch):
    secret = "supersecrettoken"
    await ns.create_channel(
        session, name="ops", webhook_url=f"https://discord.com/api/webhooks/7/{secret}"
    )
    event = await _make_event(session)

    async def failing_post(url, content):
        raise httpx.ConnectError("boom", request=httpx.Request("POST", url))

    monkeypatch.setattr(ns, "_post_discord", failing_post)
    await ns.deliver_events(session, [event])
    rows = await ns.list_deliveries(session)
    delivery = rows[0][0]
    assert secret not in json.dumps(ns.delivery_dict(delivery, rows[0][1]))
    assert "network error" in (delivery.last_error or "")


@pytest.mark.asyncio
async def test_retry_delivery_resets_failed_row(session, monkeypatch):
    await ns.create_channel(
        session, name="ops", webhook_url="https://discord.com/api/webhooks/7/token"
    )
    event = await _make_event(session)

    async def failing_post(url, content):
        return _fake_response(500)

    monkeypatch.setattr(ns, "_post_discord", failing_post)
    monkeypatch.setattr(ns, "RETRY_BACKOFF_SECONDS", 0)
    await ns.enqueue_for_events(session, [event])
    for _ in range(ns.MAX_DELIVERY_ATTEMPTS):
        await ns.dispatch_pending(session)
    rows = await ns.list_deliveries(session)
    assert rows[0][0].status == "failed"

    async def ok_post(url, content):
        return _fake_response(204)

    monkeypatch.setattr(ns, "_post_discord", ok_post)
    result = await ns.retry_delivery(session, rows[0][0].id)
    assert result is not None
    assert result[0].status == "sent"


@pytest.mark.asyncio
async def test_disabled_channel_is_skipped(session, monkeypatch):
    await ns.create_channel(
        session,
        name="ops",
        webhook_url="https://discord.com/api/webhooks/7/token",
        enabled=False,
    )
    event = await _make_event(session)
    deliveries = await ns.enqueue_for_events(session, [event])
    assert deliveries == []


# ---------------------------------------------------------------------------
# Additional providers (Slack, Telegram, generic webhook, email, browser push)
# ---------------------------------------------------------------------------


def _public_resolver(host, port, proto=None):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _private_resolver(host, port, proto=None):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", port))]


def test_slack_webhook_allowlist():
    good = "https://hooks.slack.com/services/T000/B000/XXXX"
    assert ns.validate_slack_webhook(good) == good
    with pytest.raises(ns.ChannelValidationError):
        ns.validate_slack_webhook("https://example.com/services/T/B/X")


def test_telegram_config_validation():
    config = {"bot_token": "123456789:abcdefghijklmnopqrstuvwxyz", "chat_id": "-100123"}
    assert ns.validate_telegram_config(config)["chat_id"] == "-100123"
    with pytest.raises(ns.ChannelValidationError):
        ns.validate_telegram_config({"bot_token": "nope", "chat_id": "1"})
    with pytest.raises(ns.ChannelValidationError):
        ns.validate_telegram_config({"bot_token": "123456789:abcdefghijklmnopqrstuvwxyz", "chat_id": ""})


def test_generic_webhook_rejects_private_hosts(monkeypatch):
    monkeypatch.setattr(ns.socket, "getaddrinfo", _private_resolver)
    with pytest.raises(ns.ChannelValidationError) as exc:
        ns.validate_https_url("https://internal.example.com/hook", require_public_host=True)
    assert "public internet address" in str(exc.value)

    monkeypatch.setattr(ns.socket, "getaddrinfo", _public_resolver)
    assert ns.validate_https_url("https://hooks.example.com/hook", require_public_host=True)


def test_browser_push_subscription_validation(monkeypatch):
    monkeypatch.setattr(ns.socket, "getaddrinfo", _public_resolver)
    config = {
        "subscription": {
            "endpoint": "https://push.example.com/sub/1",
            "keys": {"p256dh": "abc", "auth": "def"},
        }
    }
    normalized = ns.validate_push_subscription(config)
    assert normalized["subscription"]["endpoint"] == "https://push.example.com/sub/1"

    monkeypatch.setattr(ns.socket, "getaddrinfo", _private_resolver)
    with pytest.raises(ns.ChannelValidationError):
        ns.validate_push_subscription(config)

    with pytest.raises(ns.ChannelValidationError):
        ns.validate_push_subscription({"subscription": {"endpoint": "https://push.example.com/x", "keys": {}}})


def test_email_config_validation():
    assert ns.validate_email_config({"to": "ops@example.com"}) == {"to": "ops@example.com"}
    with pytest.raises(ns.ChannelValidationError):
        ns.validate_email_config({"to": "not-an-email"})


@pytest.mark.asyncio
async def test_multi_kind_public_dict_masks_secrets(session, monkeypatch):
    monkeypatch.setattr(ns.socket, "getaddrinfo", _public_resolver)
    telegram = await ns.create_channel(
        session,
        name="tg",
        kind="telegram",
        config={"bot_token": "123456789:supersecrettokenvalue", "chat_id": "-100999"},
    )
    public = ns.channel_public_dict(telegram)
    assert "supersecrettokenvalue" not in json.dumps(public)
    assert public["destination"].startswith("bot ")

    push = await ns.create_channel(
        session,
        name="push",
        kind="browser_push",
        config={
            "subscription": {
                "endpoint": "https://push.example.com/sub/1",
                "keys": {"p256dh": "abc", "auth": "def"},
            }
        },
    )
    push_public = ns.channel_public_dict(push)
    assert "p256dh" not in json.dumps(push_public)
    assert "push.example.com" in json.dumps(push_public)


@pytest.mark.asyncio
async def test_webhook_adapter_dispatch(session, monkeypatch):
    monkeypatch.setattr(ns.socket, "getaddrinfo", _public_resolver)
    await ns.create_channel(
        session, name="hook", kind="webhook", config={"url": "https://hooks.example.com/alert"}
    )
    event = await _make_event(session, "generic hook event")

    async def fake_post(url, content):
        assert url == "https://hooks.example.com/alert"
        assert "generic hook event" in content
        return _fake_response(204)

    monkeypatch.setattr(ns, "_post_webhook", fake_post)
    await ns.deliver_events(session, [event])
    rows = await ns.list_deliveries(session)
    assert rows[0][0].status == "sent"


@pytest.mark.asyncio
async def test_email_unavailable_without_smtp(session, monkeypatch):
    channel = await ns.create_channel(
        session, name="mail", kind="email", config={"to": "ops@example.com"}
    )
    monkeypatch.delenv("SMTP_HOST", raising=False)
    # get_settings is cached; force SMTP_HOST empty on the cached settings.
    from backend.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "SMTP_HOST", None, raising=False)
    result = await ns.send_test_message(channel)
    assert result["status"] == "failed"
    assert "SMTP" in result["error"]


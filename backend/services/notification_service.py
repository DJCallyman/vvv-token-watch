"""Durable external alert delivery (Slice 2.4).

Provider adapters: Discord, Slack, Telegram, generic HTTPS webhook, email
(SMTP), and browser push (Web Push/VAPID). Destinations that accept arbitrary
hosts (generic webhook, browser push endpoints) are resolved and rejected when
they point at private, loopback, link-local, or reserved addresses, so the
feature cannot be used for server-side request forgery. Discord and Slack are
restricted to their own webhook hosts; Telegram uses its fixed API host.

Secrets (webhook URLs, bot tokens, push subscriptions) are stored but never
returned by the API (masked instead) and never written to logs.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
import smtplib
import socket
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.db import AlertEvent, NotificationChannel, NotificationDelivery

logger = logging.getLogger(__name__)

MAX_DELIVERY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 30
HTTP_TIMEOUT_SECONDS = 10.0

CHANNEL_KINDS = ("discord", "slack", "telegram", "webhook", "email", "browser_push")

DISCORD_WEBHOOK_HOSTS = frozenset(
    {
        "discord.com",
        "www.discord.com",
        "discordapp.com",
        "www.discordapp.com",
        "ptb.discord.com",
        "canary.discord.com",
    }
)
SLACK_WEBHOOK_HOSTS = frozenset({"hooks.slack.com", "hooks.slack-gov.com"})
_TELEGRAM_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{20,}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ChannelValidationError(ValueError):
    """Raised when a channel destination is missing or unsafe."""


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return "****"
    if len(value) <= visible:
        return "****"
    return f"{value[:visible]}****"


def mask_webhook_url(url: str) -> str:
    """Return a display-safe representation of a webhook URL."""
    try:
        parsed = urlparse(url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        webhook_id = segments[-2] if len(segments) >= 2 else "unknown"
        return f"{parsed.scheme}://{parsed.hostname}/…/{webhook_id}/****"
    except Exception:
        return "https://…/****"


def _assert_public_host(host: str) -> None:
    """Reject hosts that resolve to non-public addresses (SSRF defense)."""
    if not host:
        raise ChannelValidationError("Destination host is missing")
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ChannelValidationError("Destination host could not be resolved") from exc
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            raise ChannelValidationError("Destination host resolved to an invalid address")
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise ChannelValidationError(
                "Destination must resolve to a public internet address"
            )


def validate_https_url(
    url: str,
    *,
    allowed_hosts: Optional[frozenset] = None,
    require_public_host: bool = False,
) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ChannelValidationError("Destination URL is required")
    parsed = urlparse(candidate)
    if parsed.scheme != "https":
        raise ChannelValidationError("Destination URL must use https")
    if parsed.username or parsed.password:
        raise ChannelValidationError("Destination URL must not contain credentials")
    host = (parsed.hostname or "").lower()
    if allowed_hosts is not None and host not in allowed_hosts:
        raise ChannelValidationError(
            f"Destination host must be one of: {', '.join(sorted(allowed_hosts))}"
        )
    if require_public_host:
        _assert_public_host(host)
    return candidate


def validate_discord_webhook(url: str) -> str:
    candidate = validate_https_url(url, allowed_hosts=DISCORD_WEBHOOK_HOSTS)
    segments = [segment for segment in urlparse(candidate).path.split("/") if segment]
    if len(segments) < 3 or segments[0] != "api" or segments[1] != "webhooks" or not segments[2]:
        raise ChannelValidationError("Webhook URL path must be /api/webhooks/<id>/<token>")
    return candidate


def validate_slack_webhook(url: str) -> str:
    candidate = validate_https_url(url, allowed_hosts=SLACK_WEBHOOK_HOSTS)
    segments = [segment for segment in urlparse(candidate).path.split("/") if segment]
    if len(segments) < 3 or segments[0] != "services":
        raise ChannelValidationError("Slack webhook URL path must be /services/<id>/<id>/<token>")
    return candidate


def validate_telegram_config(config: Dict[str, Any]) -> Dict[str, str]:
    token = str(config.get("bot_token") or "").strip()
    chat_id = str(config.get("chat_id") or "").strip()
    if not _TELEGRAM_TOKEN_RE.match(token):
        raise ChannelValidationError("Telegram bot token format is invalid")
    if not chat_id or len(chat_id) > 64:
        raise ChannelValidationError("Telegram chat id is required")
    return {"bot_token": token, "chat_id": chat_id}


def validate_email_config(config: Dict[str, Any]) -> Dict[str, str]:
    recipient = str(config.get("to") or "").strip()
    if not _EMAIL_RE.match(recipient):
        raise ChannelValidationError("Email recipient address is invalid")
    return {"to": recipient}


def validate_push_subscription(config: Dict[str, Any]) -> Dict[str, Any]:
    subscription = config.get("subscription")
    if not isinstance(subscription, dict):
        raise ChannelValidationError("Browser push subscription is required")
    endpoint = str(subscription.get("endpoint") or "")
    endpoint = validate_https_url(endpoint, require_public_host=True)
    keys = subscription.get("keys")
    if not isinstance(keys, dict) or not keys.get("p256dh") or not keys.get("auth"):
        raise ChannelValidationError("Browser push subscription keys are missing")
    return {"subscription": {"endpoint": endpoint, "keys": {"p256dh": keys["p256dh"], "auth": keys["auth"]}}}


def validate_channel_config(kind: str, config: Dict[str, Any]) -> Dict[str, Any]:
    if kind == "discord":
        return {"webhook_url": validate_discord_webhook(str(config.get("webhook_url") or ""))}
    if kind == "slack":
        return {"webhook_url": validate_slack_webhook(str(config.get("webhook_url") or ""))}
    if kind == "webhook":
        return {
            "url": validate_https_url(
                str(config.get("url") or ""), require_public_host=True
            )
        }
    if kind == "telegram":
        return validate_telegram_config(config)
    if kind == "email":
        return validate_email_config(config)
    if kind == "browser_push":
        return validate_push_subscription(config)
    raise ChannelValidationError(f"Unsupported channel kind '{kind}'")


def channel_config(channel: NotificationChannel) -> Dict[str, Any]:
    try:
        config = json.loads(channel.config)
    except (TypeError, json.JSONDecodeError):
        config = {}
    return config if isinstance(config, dict) else {}


def channel_public_dict(channel: NotificationChannel) -> Dict[str, Any]:
    """Channel shape safe for API responses: secrets are masked."""
    config = channel_config(channel)
    destination = None
    if channel.kind in ("discord", "slack", "webhook"):
        destination = mask_webhook_url(str(config.get("webhook_url") or config.get("url") or ""))
    elif channel.kind == "telegram":
        destination = f"bot {mask_secret(str(config.get('bot_token') or ''), 6)} → chat {mask_secret(str(config.get('chat_id') or ''))}"
    elif channel.kind == "email":
        destination = str(config.get("to") or "")
    elif channel.kind == "browser_push":
        subscription = config.get("subscription") or {}
        endpoint = str(subscription.get("endpoint") or "")
        try:
            host = urlparse(endpoint).hostname or "unknown"
        except Exception:
            host = "unknown"
        destination = f"push endpoint {host}"
    return {
        "id": channel.id,
        "kind": channel.kind,
        "name": channel.name,
        "enabled": channel.enabled,
        "destination": destination,
        "webhook_url_masked": destination if channel.kind in ("discord", "slack", "webhook") else None,
        "created_at": channel.created_at.isoformat() if channel.created_at else None,
        "updated_at": channel.updated_at.isoformat() if channel.updated_at else None,
    }


def delivery_dict(
    delivery: NotificationDelivery,
    channel: Optional[NotificationChannel] = None,
) -> Dict[str, Any]:
    return {
        "id": delivery.id,
        "alert_event_id": delivery.alert_event_id,
        "channel_id": delivery.channel_id,
        "channel_name": channel.name if channel else None,
        "channel_kind": channel.kind if channel else None,
        "status": delivery.status,
        "attempts": delivery.attempts,
        "last_error": delivery.last_error,
        "next_attempt_at": delivery.next_attempt_at.isoformat()
        if delivery.next_attempt_at
        else None,
        "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
        "updated_at": delivery.updated_at.isoformat() if delivery.updated_at else None,
    }


async def list_channels(db: AsyncSession) -> List[NotificationChannel]:
    result = await db.execute(select(NotificationChannel).order_by(NotificationChannel.id.asc()))
    return list(result.scalars().all())


async def create_channel(
    db: AsyncSession,
    *,
    name: str,
    kind: str = "discord",
    config: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None,
    enabled: bool = True,
) -> NotificationChannel:
    if kind not in CHANNEL_KINDS:
        raise ChannelValidationError(f"Unsupported channel kind '{kind}'")
    raw_config = dict(config or {})
    if webhook_url is not None:
        raw_config.setdefault("webhook_url", webhook_url)
        raw_config.setdefault("url", webhook_url)
    normalized = validate_channel_config(kind, raw_config)
    row = NotificationChannel(
        kind=kind,
        name=name,
        config=json.dumps(normalized),
        enabled=enabled,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_channel(
    db: AsyncSession,
    channel_id: int,
    *,
    name: Optional[str] = None,
    enabled: Optional[bool] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[NotificationChannel]:
    row = await db.get(NotificationChannel, channel_id)
    if row is None:
        return None
    if name is not None:
        row.name = name
    if config is not None:
        row.config = json.dumps(validate_channel_config(row.kind, config))
    if enabled is not None:
        row.enabled = enabled
    await db.commit()
    await db.refresh(row)
    return row


async def delete_channel(db: AsyncSession, channel_id: int) -> bool:
    row = await db.get(NotificationChannel, channel_id)
    if row is None:
        return False
    # Remove delivery rows first so the delete works on databases without
    # enforced FK cascades (e.g. SQLite in tests).
    from sqlalchemy import delete as sa_delete

    await db.execute(
        sa_delete(NotificationDelivery).where(NotificationDelivery.channel_id == channel_id)
    )
    await db.delete(row)
    await db.commit()
    return True


async def list_deliveries(
    db: AsyncSession,
    *,
    limit: int = 100,
    alert_event_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[Tuple[NotificationDelivery, Optional[NotificationChannel]]]:
    stmt = (
        select(NotificationDelivery, NotificationChannel)
        .join(
            NotificationChannel,
            NotificationDelivery.channel_id == NotificationChannel.id,
            isouter=True,
        )
        .order_by(NotificationDelivery.id.desc())
        .limit(limit)
    )
    if alert_event_id is not None:
        stmt = stmt.where(NotificationDelivery.alert_event_id == alert_event_id)
    if status is not None:
        stmt = stmt.where(NotificationDelivery.status == status)
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


# ---------------------------------------------------------------------------
# Provider senders
# ---------------------------------------------------------------------------


async def _post_json(url: str, payload: Dict[str, Any]) -> httpx.Response:
    """POST JSON with redirects disabled (SSRF defense)."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False) as client:
        return await client.post(
            url, json=payload, headers={"User-Agent": "vvv-token-watch/1.0"}
        )


async def _post_discord(url: str, content: str) -> httpx.Response:
    return await _post_json(url, {"content": content[:1900]})


async def _post_slack(url: str, content: str) -> httpx.Response:
    return await _post_json(url, {"text": content[:3000]})


async def _post_webhook(url: str, content: str) -> httpx.Response:
    return await _post_json(
        url, {"source": "vvv-token-watch", "type": "alert", "message": content[:4000]}
    )


async def _post_telegram(config: Dict[str, Any], content: str) -> httpx.Response:
    token = str(config.get("bot_token") or "")
    chat_id = str(config.get("chat_id") or "")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return await _post_json(
        url,
        {
            "chat_id": chat_id,
            "text": content[:4000],
            "disable_web_page_preview": True,
        },
    )


def _send_email_sync(config: Dict[str, Any], content: str) -> None:
    settings = get_settings()
    if not settings.SMTP_HOST:
        raise ChannelValidationError("SMTP is not configured")
    recipient = str(config.get("to") or "")
    sender = settings.SMTP_FROM or settings.SMTP_USERNAME or "vvv-token-watch@localhost"
    message = EmailMessage()
    message["Subject"] = "VVV Token Watch alert"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(content[:20000])
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
        smtp.send_message(message)


async def _send_email(config: Dict[str, Any], content: str) -> httpx.Response:
    try:
        await asyncio.to_thread(_send_email_sync, config, content)
    except ChannelValidationError:
        raise
    except Exception as exc:
        raise httpx.HTTPError(f"email error: {type(exc).__name__}") from exc
    return httpx.Response(
        202, request=httpx.Request("POST", "smtp://local")
    )


def _send_push_sync(config: Dict[str, Any], content: str) -> None:
    settings = get_settings()
    if not settings.VAPID_PRIVATE_KEY:
        raise ChannelValidationError("Browser push is not configured (VAPID keys missing)")
    from pywebpush import webpush

    subscription = config.get("subscription") or {}
    webpush(
        subscription_info=subscription,
        data=json.dumps({"title": "VVV Token Watch", "body": content[:500]}),
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.VAPID_SUBJECT or "mailto:admin@example.com"},
    )


async def _send_push(config: Dict[str, Any], content: str) -> httpx.Response:
    try:
        await asyncio.to_thread(_send_push_sync, config, content)
    except ChannelValidationError:
        raise
    except Exception as exc:
        raise httpx.HTTPError(f"push error: {type(exc).__name__}") from exc
    return httpx.Response(201, request=httpx.Request("POST", "webpush://local"))


async def send_channel_message(channel: NotificationChannel, content: str) -> Dict[str, Any]:
    """Send a message through a channel's adapter. Never logs or returns secrets."""
    config = channel_config(channel)
    try:
        if channel.kind == "discord":
            response = await _post_discord(validate_discord_webhook(str(config.get("webhook_url") or "")), content)
        elif channel.kind == "slack":
            response = await _post_slack(validate_slack_webhook(str(config.get("webhook_url") or "")), content)
        elif channel.kind == "webhook":
            response = await _post_webhook(
                validate_https_url(str(config.get("url") or ""), require_public_host=True),
                content,
            )
        elif channel.kind == "telegram":
            response = await _post_telegram(validate_telegram_config(config), content)
        elif channel.kind == "email":
            response = await _send_email(validate_email_config(config), content)
        elif channel.kind == "browser_push":
            response = await _send_push(validate_push_subscription(config), content)
        else:
            return {"status": "failed", "error": f"Unsupported channel kind '{channel.kind}'"}
    except ChannelValidationError as exc:
        return {"status": "failed", "error": str(exc)}
    except httpx.HTTPError as exc:
        return {"status": "failed", "error": f"network error: {type(exc).__name__}"}
    if 200 <= response.status_code < 300:
        return {"status": "sent"}
    return {"status": "failed", "error": f"Provider returned HTTP {response.status_code}"}


# ---------------------------------------------------------------------------
# Durable delivery
# ---------------------------------------------------------------------------


async def enqueue_for_events(db: AsyncSession, events: List[AlertEvent]) -> List[NotificationDelivery]:
    """Create (or reuse) a durable delivery row per event and enabled channel.

    Deduplication is enforced by the ``dedupe_key`` unique constraint, so an
    event can never be sent to the same channel twice.
    """
    if not events:
        return []
    channels = [channel for channel in await list_channels(db) if channel.enabled]
    if not channels:
        return []

    deliveries: List[NotificationDelivery] = []
    for event in events:
        for channel in channels:
            dedupe_key = f"event:{event.id}:channel:{channel.id}"
            existing = await db.execute(
                select(NotificationDelivery).where(
                    NotificationDelivery.dedupe_key == dedupe_key
                )
            )
            if existing.scalars().first() is not None:
                continue
            delivery = NotificationDelivery(
                alert_event_id=event.id,
                channel_id=channel.id,
                status="pending",
                attempts=0,
                dedupe_key=dedupe_key,
                next_attempt_at=datetime.now(timezone.utc),
            )
            try:
                async with db.begin_nested():
                    db.add(delivery)
                    await db.flush()
            except IntegrityError:
                continue
            deliveries.append(delivery)
    if deliveries:
        await db.commit()
    return deliveries


async def _attempt_delivery(
    db: AsyncSession,
    delivery: NotificationDelivery,
    channel: NotificationChannel,
) -> None:
    delivery.attempts += 1
    config = channel_config(channel)
    content = getattr(delivery, "_message", None) or (
        f"VVV Token Watch alert event #{delivery.alert_event_id}"
    )
    # Validate before sending so invalid destinations fail without a request.
    try:
        config = validate_channel_config(channel.kind, config)
    except ChannelValidationError as exc:
        delivery.status = "failed"
        delivery.last_error = f"invalid destination: {exc}"
        await db.commit()
        return

    channel.config = json.dumps(config)
    try:
        if channel.kind == "discord":
            response = await _post_discord(config["webhook_url"], content)
        elif channel.kind == "slack":
            response = await _post_slack(config["webhook_url"], content)
        elif channel.kind == "webhook":
            response = await _post_webhook(config["url"], content)
        elif channel.kind == "telegram":
            response = await _post_telegram(config, content)
        elif channel.kind == "email":
            response = await _send_email(config, content)
        elif channel.kind == "browser_push":
            response = await _send_push(config, content)
        else:
            delivery.status = "failed"
            delivery.last_error = f"unsupported channel kind '{channel.kind}'"
            await db.commit()
            return
    except httpx.HTTPError as exc:
        _schedule_retry(delivery, f"network error: {type(exc).__name__}")
        await db.commit()
        return
    except ChannelValidationError as exc:
        delivery.status = "failed"
        delivery.last_error = str(exc)
        delivery.next_attempt_at = None
        await db.commit()
        return

    if 200 <= response.status_code < 300:
        delivery.status = "sent"
        delivery.last_error = None
        delivery.next_attempt_at = None
    elif response.status_code == 429:
        retry_after = _retry_after_seconds(response)
        _schedule_retry(delivery, "rate limited by provider", retry_after=retry_after)
    elif response.status_code >= 500:
        _schedule_retry(delivery, f"Provider returned HTTP {response.status_code}")
    else:
        delivery.status = "failed"
        delivery.last_error = f"Provider rejected the message (HTTP {response.status_code})"
        delivery.next_attempt_at = None
    await db.commit()


def _retry_after_seconds(response: httpx.Response) -> Optional[float]:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _schedule_retry(
    delivery: NotificationDelivery,
    error: str,
    *,
    retry_after: Optional[float] = None,
) -> None:
    delivery.last_error = error
    if delivery.attempts >= MAX_DELIVERY_ATTEMPTS:
        delivery.status = "failed"
        delivery.next_attempt_at = None
        return
    delay = retry_after if retry_after is not None else RETRY_BACKOFF_SECONDS * (2 ** (delivery.attempts - 1))
    delivery.status = "pending"
    delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)


def delivery_message(delivery: NotificationDelivery, channel: NotificationChannel) -> str:
    message = getattr(delivery, "_message", None)
    if message:
        return message
    return f"VVV Token Watch alert event #{delivery.alert_event_id}"


async def dispatch_pending(db: AsyncSession, limit: int = 20) -> List[NotificationDelivery]:
    """Send pending deliveries that are due. Returns the deliveries attempted."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(NotificationDelivery, NotificationChannel)
        .join(NotificationChannel, NotificationDelivery.channel_id == NotificationChannel.id)
        .where(NotificationDelivery.status == "pending")
        .order_by(NotificationDelivery.id.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    pairs = [(row[0], row[1]) for row in result.all()]
    attempted: List[NotificationDelivery] = []
    for delivery, channel in pairs:
        if delivery.next_attempt_at is not None:
            next_attempt = delivery.next_attempt_at
            if next_attempt.tzinfo is None:
                next_attempt = next_attempt.replace(tzinfo=timezone.utc)
            if next_attempt > now:
                continue
        # Attach the alert message for the adapter without an extra query per row.
        event = await db.get(AlertEvent, delivery.alert_event_id)
        if event is not None:
            delivery._message = f"[VVV Token Watch] {event.message}"
        await _attempt_delivery(db, delivery, channel)
        attempted.append(delivery)
    return attempted


async def deliver_events(db: AsyncSession, events: List[AlertEvent]) -> None:
    """Enqueue and immediately attempt delivery. Never raises to the caller."""
    try:
        await enqueue_for_events(db, events)
        await dispatch_pending(db)
    except Exception:
        logger.exception("External alert delivery failed")


async def send_test_message(channel: NotificationChannel) -> Dict[str, Any]:
    """Send a test message synchronously. Never logs or returns secrets."""
    return await send_channel_message(
        channel,
        "VVV Token Watch test notification — channel is configured correctly.",
    )


async def retry_delivery(
    db: AsyncSession,
    delivery_id: int,
) -> Optional[Tuple[NotificationDelivery, Optional[NotificationChannel]]]:
    row = await db.get(NotificationDelivery, delivery_id)
    if row is None:
        return None
    if row.status == "sent":
        return (row, await db.get(NotificationChannel, row.channel_id))
    row.status = "pending"
    row.attempts = 0
    row.last_error = None
    row.next_attempt_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    channel = await db.get(NotificationChannel, row.channel_id)
    await dispatch_pending(db)
    await db.refresh(row)
    return (row, channel)

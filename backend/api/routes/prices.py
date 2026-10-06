import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.core import venicestats_client
from backend.core.venicestats_client import VeniceStatsError
from backend.database import get_db
from backend.limiter import limiter
from backend.services.price_history_service import get_price_history, record_price_snapshot
from backend.services import alert_engine, notification_service
from backend.services.app_settings import get_effective_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/prices")
async def get_prices(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    try:
        effective = await get_effective_settings(db, settings)
        metrics = await venicestats_client.get_metrics(settings)

        vvv_usd = metrics.get("vvvPrice")
        diem_usd = metrics.get("diemPrice")
        if not isinstance(vvv_usd, (int, float)) or not isinstance(diem_usd, (int, float)):
            raise VeniceStatsError("Metrics payload missing prices")

        # Resolve holding amounts from the selected source. Wallet mode
        # reads balances from venicestats /api/venetians (60s TTL) and
        # falls back to the manual amounts when the fetch fails or no
        # address is set.
        #
        # VVV holdings include the full position: unstaked VVV, the staked
        # sVVV position (locked + unlocked), and unclaimed staking rewards.
        # DIEM holdings include unstaked DIEM plus DIEM locked in staking.
        vvv_manual = effective["coingecko_holding_amount"]
        diem_manual = effective["diem_holding_amount"]
        vvv_wallet_amount = vvv_manual
        svvv_amount = 0.0
        unclaimed_rewards = 0.0
        diem_wallet_amount = diem_manual
        diem_staked_amount = 0.0
        vvv_holding = vvv_manual
        diem_holding = diem_manual
        holdings_source = "manual"
        if effective.get("vvv_holding_source") == "wallet":
            wallet = (effective.get("vvv_wallet_address") or "").strip()
            if not wallet:
                logger.warning("Wallet holding source selected but no wallet address set; using manual amounts")
            else:
                try:
                    holdings = await venicestats_client.get_wallet_holdings(wallet, settings)
                    vvv_wallet_amount = holdings["vvv_wallet"]
                    svvv_amount = holdings["svvv_total"]
                    unclaimed_rewards = holdings["pending_rewards"]
                    diem_wallet_amount = holdings["diem_wallet"]
                    diem_staked_amount = holdings["diem_staked"]
                    vvv_holding = (
                        vvv_wallet_amount + svvv_amount + unclaimed_rewards
                    )
                    diem_holding = diem_wallet_amount + diem_staked_amount
                    holdings_source = "wallet"
                except Exception:
                    logger.exception("Wallet holdings fetch failed; falling back to manual amounts")

        # AUD support via daily ECB FX rates (frankfurter.dev). If the FX
        # service is unavailable, degrade gracefully: omit aud rather than
        # failing the whole price poll.
        aud_rate: Optional[float] = None
        try:
            aud_rate = await venicestats_client.get_usd_aud_rate(settings)
        except VeniceStatsError:
            logger.warning("FX rate unavailable; omitting AUD prices this poll")

        def _aud(usd: Optional[float]) -> Optional[float]:
            if usd is None or aud_rate is None:
                return None
            return round(usd * aud_rate, 6)

        vvv_change = metrics.get("priceChange24h")
        diem_change = metrics.get("diemPriceChange24h")
        vvv_mcap = metrics.get("marketCap")
        diem_mcap = metrics.get("diemMarketCap")

        result = {
            "vvv": {
                "usd": vvv_usd,
                "aud": _aud(vvv_usd),
                "change_24h": vvv_change,
                "market_cap": vvv_mcap,
                "fdv": metrics.get("fdv"),
            },
            "diem": {
                "usd": diem_usd,
                "aud": _aud(diem_usd),
                "change_24h": diem_change,
                "market_cap": diem_mcap,
                "fdv": metrics.get("diemFdv"),
            },
            "holdings": {
                "vvv": vvv_holding,
                "diem": diem_holding,
                "vvv_source": holdings_source,
                "diem_source": holdings_source,
                "vvv_wallet": vvv_wallet_amount,
                "svvv": svvv_amount,
                "unclaimed_rewards": unclaimed_rewards,
                "diem_wallet": diem_wallet_amount,
                "diem_staked": diem_staked_amount,
            }
        }

        vvv_value_usd = vvv_wallet_amount * vvv_usd
        svvv_value_usd = svvv_amount * vvv_usd
        rewards_value_usd = unclaimed_rewards * vvv_usd
        diem_value_usd = diem_holding * diem_usd
        gross_exposure_usd = vvv_value_usd + svvv_value_usd + rewards_value_usd + diem_value_usd
        # The held DIEM is treated as the cost to unlock the locked sVVV,
        # so it contributes to gross exposure but is netted from net worth.
        diem_unlock_offset_usd = diem_value_usd
        net_worth_usd = gross_exposure_usd - diem_unlock_offset_usd
        result["portfolio"] = {
            "vvv_value_usd": vvv_value_usd,
            "svvv_value_usd": svvv_value_usd,
            "unclaimed_rewards_value_usd": rewards_value_usd,
            "diem_value_usd": diem_value_usd,
            "gross_exposure_usd": gross_exposure_usd,
            "diem_unlock_offset_usd": diem_unlock_offset_usd,
            "net_worth_usd": net_worth_usd,
            "total_usd": gross_exposure_usd,
        }

        # Persist snapshots for history charts (best-effort). market_cap and
        # change_24h columns existed but were never populated until now.
        try:
            await record_price_snapshot(
                db,
                token_id="vvv",
                price_usd=vvv_usd,
                price_aud=result["vvv"].get("aud"),
                market_cap=vvv_mcap if isinstance(vvv_mcap, (int, float)) else None,
                change_24h=vvv_change if isinstance(vvv_change, (int, float)) else None,
            )
            await record_price_snapshot(
                db,
                token_id="diem",
                price_usd=diem_usd,
                price_aud=result["diem"].get("aud"),
                market_cap=diem_mcap if isinstance(diem_mcap, (int, float)) else None,
                change_24h=diem_change if isinstance(diem_change, (int, float)) else None,
            )
        except Exception:
            logger.exception("Failed to persist price snapshots")

        # Best-effort price threshold alerts.
        # BUG-07: only include metrics that have real present values.
        # Do not feed 0.0 for missing tokens/currencies (would spuriously fire lte alerts).
        price_alert_metrics: dict[str, float] = {}
        if vvv_usd is not None:
            try:
                price_alert_metrics["vvv_price_usd"] = float(vvv_usd)
            except Exception:
                pass
        if diem_usd is not None:
            try:
                price_alert_metrics["diem_price_usd"] = float(diem_usd)
            except Exception:
                pass

        if price_alert_metrics:
            try:
                history: dict = {}
                for token_id in ("vvv", "diem"):
                    points = await get_price_history(db, token_id=token_id, range_key="24h")
                    metric_key = f"{token_id}_price_usd"
                    history[metric_key] = [
                        {"timestamp": point.get("timestamp"), "value": point.get("price_usd")}
                        for point in points
                        if point.get("price_usd") is not None
                    ]
                events = await alert_engine.evaluate_alerts(
                    db, price_alert_metrics, history
                )
                await notification_service.deliver_events(db, events)
            except Exception:
                logger.exception("Alert evaluation failed during price poll")

        return result
    except VeniceStatsError as e:
        raise HTTPException(status_code=502, detail=f"VeniceStats API error: {e}")
    except Exception:
        logger.exception("Failed to fetch prices")
        raise HTTPException(status_code=500, detail="Failed to fetch prices")


@router.get("/prices/history")
async def get_prices_history(
    token: str = Query("vvv", pattern="^(vvv|diem)$"),
    range: str = Query("7d", pattern="^(24h|7d|30d|90d)$", alias="range"),
    db: AsyncSession = Depends(get_db),
):
    """Return persisted price snapshots for charts."""
    try:
        points = await get_price_history(db, token_id=token, range_key=range)
        return {"token": token, "range": range, "count": len(points), "data": points}
    except Exception:
        logger.exception("Failed to fetch price history")
        raise HTTPException(status_code=500, detail="Failed to fetch price history")


@router.get("/prices/{token_id}")
@limiter.limit("60/hour")
async def get_token_price(
    request: Request,
    token_id: str,
    settings: Settings = Depends(get_settings)
):
    """Single-token lookup served from the venicestats KPI payload.

    Only VVV/DIEM are exposed by venicestats; other ids return 404.
    """
    if token_id not in ("vvv", "diem"):
        raise HTTPException(status_code=404, detail=f"Token '{token_id}' not found")
    try:
        metrics = await venicestats_client.get_metrics(settings)
        if token_id == "vvv":
            prices = {
                "usd": metrics.get("vvvPrice"),
                "aud": None,
                "change_24h": metrics.get("priceChange24h"),
                "market_cap": metrics.get("marketCap"),
            }
        else:
            prices = {
                "usd": metrics.get("diemPrice"),
                "aud": None,
                "change_24h": metrics.get("diemPriceChange24h"),
                "market_cap": metrics.get("diemMarketCap"),
            }
        if prices["usd"] is None:
            raise HTTPException(status_code=404, detail=f"Token '{token_id}' not found")
        try:
            prices["aud"] = round(prices["usd"] * await venicestats_client.get_usd_aud_rate(settings), 6)
        except VeniceStatsError:
            pass
        return {"token_id": token_id, "prices": prices}
    except HTTPException:
        raise
    except VeniceStatsError as e:
        raise HTTPException(status_code=502, detail=f"VeniceStats API error: {e}")
    except Exception:
        logger.exception("Failed to fetch token price")
        raise HTTPException(status_code=500, detail="Failed to fetch token price")

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.database import get_db
from backend.limiter import limiter
from backend.services.price_history_service import get_price_history, record_price_snapshot
from backend.services import alert_engine

logger = logging.getLogger(__name__)
router = APIRouter()


async def fetch_coin_gecko_price(
    token_id: str,
    currencies: list[str],
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> dict:
    settings = get_settings()
    base_url = base_url or settings.COINGECKO_API_BASE_URL
    params = {
        "ids": token_id,
        "vs_currencies": ",".join(currencies)
    }
    headers = {}

    if api_key:
        if api_key.startswith("CG-"):
            headers["x-cg-demo-api-key"] = api_key
        else:
            headers["x-cg-pro-api-key"] = api_key
            base_url = "https://pro-api.coingecko.com/api/v3"

    url = f"{base_url}/simple/price"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


@router.get("/prices")
async def get_prices(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    try:
        vvv_data = await fetch_coin_gecko_price(
            settings.COINGECKO_TOKEN_ID,
            settings.coingecko_currencies_list,
            settings.COINGECKO_API_KEY
        )

        diem_data = await fetch_coin_gecko_price(
            settings.DIEM_TOKEN_ID,
            settings.coingecko_currencies_list,
            settings.COINGECKO_API_KEY
        )

        result = {
            "vvv": {},
            "diem": {},
            "holdings": {
                "vvv": settings.COINGECKO_HOLDING_AMOUNT,
                "diem": settings.DIEM_HOLDING_AMOUNT
            }
        }

        if settings.COINGECKO_TOKEN_ID in vvv_data:
            for currency in settings.coingecko_currencies_list:
                if currency in vvv_data[settings.COINGECKO_TOKEN_ID]:
                    result["vvv"][currency] = vvv_data[settings.COINGECKO_TOKEN_ID][currency]

        if settings.DIEM_TOKEN_ID in diem_data:
            for currency in settings.coingecko_currencies_list:
                if currency in diem_data[settings.DIEM_TOKEN_ID]:
                    result["diem"][currency] = diem_data[settings.DIEM_TOKEN_ID][currency]

        if "usd" in result["vvv"]:
            result["portfolio"] = {
                "vvv_value_usd": settings.COINGECKO_HOLDING_AMOUNT * result["vvv"].get("usd", 0),
                "diem_value_usd": settings.DIEM_HOLDING_AMOUNT * result["diem"].get("usd", 0),
                "total_usd": (
                    settings.COINGECKO_HOLDING_AMOUNT * result["vvv"].get("usd", 0) +
                    settings.DIEM_HOLDING_AMOUNT * result["diem"].get("usd", 0)
                )
            }

        # Persist snapshots for history charts (best-effort).
        try:
            await record_price_snapshot(
                db,
                token_id="vvv",
                price_usd=result["vvv"].get("usd"),
                price_aud=result["vvv"].get("aud"),
            )
            await record_price_snapshot(
                db,
                token_id="diem",
                price_usd=result["diem"].get("usd"),
                price_aud=result["diem"].get("aud"),
            )
        except Exception:
            logger.exception("Failed to persist price snapshots")

        # Best-effort price threshold alerts.
        # BUG-07: only include metrics that have real present values.
        # Do not feed 0.0 for missing tokens/currencies (would spuriously fire lte alerts).
        price_alert_metrics: dict[str, float] = {}
        vvv_usd = result["vvv"].get("usd")
        if vvv_usd is not None:
            try:
                price_alert_metrics["vvv_price_usd"] = float(vvv_usd)
            except Exception:
                pass
        diem_usd = result["diem"].get("usd")
        if diem_usd is not None:
            try:
                price_alert_metrics["diem_price_usd"] = float(diem_usd)
            except Exception:
                pass

        if price_alert_metrics:
            try:
                await alert_engine.evaluate_alerts(db, price_alert_metrics)
            except Exception:
                logger.exception("Alert evaluation failed during price poll")

        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"CoinGecko API error: {e}")
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
    try:
        data = await fetch_coin_gecko_price(
            token_id,
            settings.coingecko_currencies_list,
            settings.COINGECKO_API_KEY
        )

        if token_id not in data:
            raise HTTPException(status_code=404, detail=f"Token '{token_id}' not found")

        return {
            "token_id": token_id,
            "prices": data[token_id]
        }
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"CoinGecko API error: {e}")
    except Exception:
        logger.exception("Failed to fetch token price")
        raise HTTPException(status_code=500, detail="Failed to fetch token price")

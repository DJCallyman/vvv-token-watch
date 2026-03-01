from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import httpx
from backend.config import get_settings, Settings

router = APIRouter()


async def fetch_coin_gecko_price(
    token_id: str,
    currencies: list[str],
    api_key: Optional[str] = None
) -> dict:
    url = "https://api.coingecko.com/api/v3/simple/price"
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
            url = "https://pro-api.coingecko.com/api/v3/simple/price"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


@router.get("/prices")
async def get_prices(settings: Settings = Depends(get_settings)):
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
        
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"CoinGecko API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/{token_id}")
async def get_token_price(
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
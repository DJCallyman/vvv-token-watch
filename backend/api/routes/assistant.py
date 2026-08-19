"""Natural-language read-only assistant for application data."""

from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from backend.api.routes.ai_common import extract_chat_text, get_client
from backend.api.routes.onchain import _fetch_vvv_erc20_meta, VVV_TOKEN, STAKING_CONTRACT, NETWORK
from backend.api.routes.prices import fetch_coin_gecko_price
from backend.config import Settings, get_settings
from backend.core.usage_tracker import UsageTracker
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class AssistantRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list, max_length=20)


TOOL_DESCRIPTIONS = {
    "get_balance": "Get the current DIEM and USD account balance.",
    "get_prices": "Get the current VVV and DIEM token prices and configured portfolio value.",
    "get_usage": "Get current epoch DIEM, USD, and bundled-credit usage.",
    "get_onchain": "Get current VVV total supply, circulating estimate, and staking amount.",
}


def _assistant_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        }
        for name, description in TOOL_DESCRIPTIONS.items()
    ]


def _detect_assistant_tool(query: str) -> str | None:
    normalized = query.lower()
    if any(term in normalized for term in ("balance", "credit", "diem balance", "usd balance")):
        return "get_balance"
    if any(term in normalized for term in ("price", "worth", "portfolio")):
        return "get_prices"
    if any(term in normalized for term in ("usage", "spent", "spending", "consumed")):
        return "get_usage"
    if any(term in normalized for term in ("supply", "staking", "staked", "circulating")):
        return "get_onchain"
    return None


async def _run_assistant_tool(name: str, client, settings: Settings) -> dict:
    if name == "get_balance":
        billing = await client.get_json("/billing/balance")
        balance = billing.get("data", {})
        balances = balance.get("balances", {})
        diem_value = balances.get("DIEM", balances.get("diem"))
        usd_value = balances.get("USD", balances.get("usd"))
        if diem_value is None or usd_value is None:
            rate_limits = await UsageTracker(client.api_key, client).fetch_rate_limits()
            if diem_value is None:
                diem_value = rate_limits.diem
            if usd_value is None:
                usd_value = rate_limits.usd
        return {
            "diem": float(diem_value),
            "usd": float(usd_value),
            "consumption_currency": balance.get("consumptionCurrency"),
            "can_consume": balance.get("canConsume"),
        }

    if name == "get_prices":
        currencies = settings.coingecko_currencies_list
        vvv = await fetch_coin_gecko_price(
            settings.COINGECKO_TOKEN_ID, currencies, settings.COINGECKO_API_KEY
        )
        diem = await fetch_coin_gecko_price(
            settings.DIEM_TOKEN_ID, currencies, settings.COINGECKO_API_KEY
        )
        vvv_prices = vvv.get(settings.COINGECKO_TOKEN_ID, {})
        diem_prices = diem.get(settings.DIEM_TOKEN_ID, {})
        return {
            "vvv": vvv_prices,
            "diem": diem_prices,
            "holdings": {
                "vvv": settings.COINGECKO_HOLDING_AMOUNT,
                "diem": settings.DIEM_HOLDING_AMOUNT,
            },
        }

    if name == "get_usage":
        tracker = UsageTracker(client.api_key, client)
        return await tracker.get_epoch_usage()

    if name == "get_onchain":
        meta = await _fetch_vvv_erc20_meta(client)
        scale = 10 ** meta["decimals"]
        total = meta["total_raw"] / scale
        staked = meta["staked_raw"] / scale
        return {
            "network": NETWORK,
            "token_address": VVV_TOKEN,
            "staking_contract": STAKING_CONTRACT,
            "total_supply": total,
            "staked_in_contract": staked,
            "circulating_estimate": max(total - staked, 0.0),
        }

    raise ValueError(f"Unknown assistant tool: {name}")


@router.post("/assistant/query")
@limiter.limit("30/hour")
async def query_assistant(request: Request, settings: Settings = Depends(get_settings)):
    try:
        raw_body = await request.json()
        body = AssistantRequest.model_validate(
            raw_body if isinstance(raw_body, dict) else {}
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON body: {exc}") from exc

    client = get_client(settings)
    tools = _assistant_tools()
    live_tool = _detect_assistant_tool(body.query)
    live_data = None
    if live_tool:
        try:
            live_data = await _run_assistant_tool(live_tool, client, settings)
        except Exception as exc:
            logger.exception("Assistant prefetch tool %s failed", live_tool)
            live_data = {"error": f"Unable to retrieve {live_tool}: {exc}"}

    if live_tool == "get_balance":
        if "error" in live_data:
            return {"answer": "I could not retrieve the current balance.", "tool_calls": []}
        return {
            "answer": (
                f"Your current balance is {live_data['diem']} DIEM "
                f"and {live_data['usd']} USD."
            ),
            "tool_calls": [],
        }

    system_message = "You are the read-only VVV Token Watch assistant. For current data, use only the supplied live data or tool results. Never guess, invent, or use example values. Clearly say when live data could not be retrieved. Never provide financial advice."
    if live_tool:
        system_message += f"\nLive data for {live_tool}: {json.dumps(live_data, default=str)}"
    messages = [{"role": "system", "content": system_message}, *body.history[-20:], {"role": "user", "content": body.query}]
    try:
        if live_tool:
            completion = await client.post_json("/chat/completions", data={"model": "venice-uncensored-1-2", "messages": messages, "tool_choice": "none", "max_tokens": 1000, "venice_parameters": {"include_venice_system_prompt": False}}, timeout=60)
            return {"answer": extract_chat_text(completion), "tool_calls": []}

        all_tool_calls = []
        for _ in range(3):
            completion = await client.post_json("/chat/completions", data={"model": "venice-uncensored-1-2", "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 1000, "venice_parameters": {"include_venice_system_prompt": False}}, timeout=60)
            message = (completion.get("choices") or [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls") or []
            all_tool_calls.extend(tool_calls)
            if not tool_calls:
                return {"answer": extract_chat_text(completion), "tool_calls": all_tool_calls}

            messages.append(message)
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name")
                try:
                    result = await _run_assistant_tool(name, client, settings)
                except Exception as exc:
                    logger.exception("Assistant tool %s failed", name)
                    result = {"error": f"Unable to retrieve {name}: {exc}"}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", name),
                    "name": name,
                    "content": json.dumps(result, default=str),
                })

        raise HTTPException(status_code=502, detail="Assistant exceeded tool-call limit")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "Venice assistant failed") from exc
    except Exception as exc:
        logger.exception("Assistant request failed")
        raise HTTPException(500, "Failed to answer request") from exc

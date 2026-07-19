#!/usr/bin/env python3
"""Venice text-model benchmark runner (T1–T8).

Spawned by backend/api/routes/benchmark.py as a subprocess. Also runnable
standalone for local debugging.

CLI contract (must stay in sync with backend start_benchmark):
  --api-key, --iterations, --workers, --privacy, --output, --yes,
  --no-infographic, --tests, --models

Stdout protocol:
  - Human-readable log lines (streamed to the UI terminal)
  - ##PROGRESS## {completed}/{total} after each model finishes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VENICE_BASE = "https://api.venice.ai/api/v1"
REQUEST_TIMEOUT_S = 60.0
ALL_TESTS = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]

# Composite score weights (must sum to 1.0)
WEIGHTS = {
    "T1": 0.10,
    "T2": 0.15,
    "T3": 0.15,
    "T4": 0.10,
    "T5": 0.15,
    "T6": 0.10,
    "T7": 0.10,
    "T8": 0.15,
}

def _estimate_tokens(text: str) -> int:
    """Rough token count from text length.

    Uses ~4 characters per token for English text, plus a small overhead for
    message formatting / special tokens.
    """
    if not text:
        return 0
    return max(1, int(len(text) / 4.0) + 4)


# Venice adds message-formatting overhead to every call (system prompt is
# disabled via venice_parameters). Calibrated against observed T7 usage:
# user prompt ~12 tokens, billed prompt ~199 tokens.
VENICE_PROMPT_OVERHEAD_TOKENS = 180

# Models that always generate reasoning tokens regardless of max_tokens or
# reasoning controls. Estimates for these models should use historical observed
# completion averages rather than max_tokens ceilings.
ALWAYS_REASONING_MODELS = {
    "grok-build-0-1",
    "grok-4-3",
    "grok-4-5",
    "grok-4-20",
    "grok-4-20-multi-agent",
}

# Fallback completion estimates per test when no historical data exists.
# These are max_tokens ceilings; actual reasoning models will usually exceed them.
DEFAULT_COMPLETION_ESTIMATES = {
    "T1": 64,
    "T2": 256,
    "T3": 256,
    "T4": 256,
    "T5": 512,
    "T6": 128 * 3,
    "T7": 32,
    "T8": 128,
}


def _estimate_message_tokens(messages: list[dict], extra_text: str = "") -> int:
    """Estimate prompt tokens from a list of chat messages."""
    total = VENICE_PROMPT_OVERHEAD_TOKENS
    for msg in messages:
        total += _estimate_tokens(msg.get("content", ""))
        total += 2  # role / message overhead
    total += _estimate_tokens(extra_text)
    return total


def _load_historical_completion_estimates(output_dir: Path) -> dict[str, dict[str, float]]:
    """Load observed completion token means per (model_id, test_id) from prior runs.

    Returns a dict: {model_id: {test_id: mean_completion_tokens}}.
    Only includes entries with at least one successful run.
    """
    estimates: dict[str, dict[str, float]] = {}
    if not output_dir.exists():
        return estimates

    for path in sorted(output_dir.glob("benchmark_*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for model in data.get("models", []):
            model_id = model.get("model_id")
            if not model_id:
                continue
            model_est = estimates.setdefault(model_id, {})
            for tid, cat in model.get("categories", {}).items():
                if cat.get("skipped") or cat.get("runs_success", 0) == 0:
                    continue
                mean = cat.get("tokens_completion_mean")
                if mean is None:
                    continue
                # Keep the most recent observation (files are sorted by mtime)
                model_est[tid] = float(mean)
    return estimates


def _test_token_estimates(
    tid: str,
    model_id: str = "",
    historical_estimates: Optional[dict[str, dict[str, float]]] = None,
) -> tuple[int, int]:
    """Return (estimated_prompt_tokens, estimated_completion_tokens) per iteration.

    Prompt estimates are derived from the actual prompts the test sends.
    Completion estimates prefer historical observed means when available,
    otherwise fall back to max_tokens ceilings. For models known to always
    reason (e.g. Grok), historical data is strongly preferred.
    """
    if historical_estimates and model_id:
        hist = historical_estimates.get(model_id, {}).get(tid)
        if hist is not None:
            return _prompt_estimate_for_test(tid), int(hist)

    # No historical data: use default ceiling. For always-reasoning models this
    # will be a significant underestimate, which we flag in the estimate UI.
    return _prompt_estimate_for_test(tid), DEFAULT_COMPLETION_ESTIMATES.get(tid, 50)


def _prompt_estimate_for_test(tid: str) -> int:
    """Estimate prompt tokens for a test from its actual prompt(s)."""
    if tid == "T1":
        messages = [{"role": "user", "content": "Count from 1 to 5."}]
        return _estimate_message_tokens(messages)
    if tid == "T2":
        messages = [
            {
                "role": "user",
                "content": "What's the weather in Tokyo right now? Use the get_weather tool.",
            }
        ]
        tools_text = json.dumps(WEATHER_TOOLS)
        return _estimate_message_tokens(messages, tools_text)
    if tid == "T3":
        messages = [{"role": "user", "content": PERSON_PROMPT}]
        schema_text = json.dumps(PERSON_SCHEMA)
        return _estimate_message_tokens(messages, schema_text)
    if tid == "T4":
        messages = [{"role": "user", "content": T4_PROMPT}]
        return _estimate_message_tokens(messages)
    if tid == "T5":
        messages = [{"role": "user", "content": T5_PROMPT}]
        return _estimate_message_tokens(messages)
    if tid == "T6":
        turns = [
            "My favorite color is blue and my pet's name is Whiskers.",
            "What is 12 + 30?",
            "What is my favorite color and my pet's name?",
        ]
        history: list[dict] = []
        total_prompt = 0
        for turn in turns:
            history.append({"role": "user", "content": turn})
            total_prompt += _estimate_message_tokens(history)
            history.append({"role": "assistant", "content": "ok"})
        return total_prompt
    if tid == "T7":
        messages = [{"role": "user", "content": T7_PROMPT}]
        return _estimate_message_tokens(messages)
    if tid == "T8":
        messages = [{"role": "user", "content": T8_PROMPT}]
        return _estimate_message_tokens(messages)
    return 50

# ---------------------------------------------------------------------------
# Logging helpers (stdout is consumed by SSE)
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, flush=True)


def progress(done: int, total: int, model_id: str = "") -> None:
    suffix = f" {model_id}" if model_id else ""
    print(f"##PROGRESS## {done}/{total}{suffix}", flush=True)


# ---------------------------------------------------------------------------
# Model fetch / filter (mirrors backend/api/routes/benchmark.py)
# ---------------------------------------------------------------------------

def _is_e2ee_or_tee(model: dict) -> bool:
    caps = (model.get("model_spec") or {}).get("capabilities") or {}
    return (
        caps.get("supportsE2EE") is True
        or caps.get("supportsTeeAttestation") is True
        or (model.get("id") or "").startswith("e2ee-")
    )


def extract_model_meta(m: dict) -> dict:
    spec = m.get("model_spec") or {}
    caps = spec.get("capabilities") or {}
    pricing = spec.get("pricing") or {}
    return {
        "id": m.get("id", ""),
        "privacy": (spec.get("privacy") or "unknown").lower(),
        "context_length": (
            spec.get("availableContextTokens")
            or spec.get("context_length")
            or 0
        ),
        "max_completion_tokens": (
            spec.get("maxCompletionTokens")
            or spec.get("max_output_tokens")
            or 0
        ),
        "capabilities": {
            "supportsFunctionCalling": bool(caps.get("supportsFunctionCalling", False)),
            "supportsReasoning": bool(caps.get("supportsReasoning", False)),
            "supportsReasoningEffort": bool(caps.get("supportsReasoningEffort", False)),
            "supportsResponseSchema": bool(caps.get("supportsResponseSchema", False)),
            "supportsVision": bool(caps.get("supportsVision", False)),
        },
        "pricing_input_usd": (pricing.get("input") or {}).get("usd"),
        "pricing_output_usd": (pricing.get("output") or {}).get("usd"),
        "description": spec.get("description") or "",
    }


async def fetch_qualifying_models(
    client: httpx.AsyncClient,
    privacy: str,
) -> list[dict]:
    """Fetch text models and filter to private/anonymized, non-E2EE/TEE."""
    resp = await client.get(f"{VENICE_BASE}/models", params={"type": "text"})
    resp.raise_for_status()
    raw = resp.json().get("data", [])

    allowed = {"private", "anonymized"} if privacy == "both" else {privacy}
    result = []
    for m in raw:
        spec = m.get("model_spec") or {}
        p = (spec.get("privacy") or "").lower()
        if p not in allowed:
            continue
        if _is_e2ee_or_tee(m):
            continue
        result.append(m)
    return sorted(result, key=lambda x: x.get("id", ""))


# ---------------------------------------------------------------------------
# Cost estimate + confirmation gate
# ---------------------------------------------------------------------------

def estimate_cost(
    models: list[dict],
    tests: list[str],
    iterations: int,
    output_dir: Path,
) -> tuple[int, float, list[str]]:
    """Return (estimated_api_calls, estimated_usd, warning_messages).

    Completion estimates use historical observed means when available.
    For models known to always reason without a historical sample, a warning
    is returned because the estimate will likely be too low.
    """
    historical = _load_historical_completion_estimates(output_dir)
    total_calls = 0
    total_usd = 0.0
    warnings: list[str] = []

    for m in models:
        meta = extract_model_meta(m)
        model_id = meta["id"]
        caps = meta["capabilities"]
        pin = meta["pricing_input_usd"] or 0.0
        pout = meta["pricing_output_usd"] or 0.0

        for tid in tests:
            # Skip tests the model cannot run
            if tid == "T2" and not caps["supportsFunctionCalling"]:
                continue
            # T6 is multi-turn: ~3 API calls per iteration
            calls_per_iter = 3 if tid == "T6" else 1
            calls = calls_per_iter * iterations
            total_calls += calls

            prompt_tok, completion_tok = _test_token_estimates(
                tid, model_id=model_id, historical_estimates=historical
            )
            # pricing is $/1M tokens
            cost = (
                (prompt_tok * calls * pin / 1_000_000)
                + (completion_tok * calls * pout / 1_000_000)
            )
            total_usd += cost

            if model_id in ALWAYS_REASONING_MODELS and tid not in historical.get(model_id, {}):
                warnings.append(
                    f"  WARNING: {model_id} always generates reasoning tokens; "
                    f"{tid} estimate uses max_tokens ceiling and will likely be too low."
                )

    return total_calls, total_usd, warnings


def confirm_or_exit(
    models: list[dict],
    tests: list[str],
    iterations: int,
    workers: int,
    yes: bool,
    output_dir: Path,
) -> None:
    calls, usd, warnings = estimate_cost(models, tests, iterations, output_dir)
    log("=" * 60)
    log("BENCHMARK COST ESTIMATE")
    log(f"  Models:     {len(models)}")
    log(f"  Tests:      {', '.join(tests)}")
    log(f"  Iterations: {iterations}")
    log(f"  Workers:    {workers}")
    log(f"  Est. calls: ~{calls:,}")
    log(f"  Est. cost:  ~${usd:.4f} USD")
    if warnings:
        log("  Warnings:")
        for w in warnings:
            log(w)
    log("  (estimate uses historical averages where available; actual cost may vary)")
    log("=" * 60)

    if yes:
        log("Auto-confirmed via --yes")
        return

    if not sys.stdin.isatty():
        log("ERROR: Non-interactive stdin and --yes not set. Aborting.")
        log("Pass --yes to skip confirmation (used by the web UI).")
        sys.exit(2)

    try:
        answer = input("Proceed with benchmark? [y/N] ").strip().lower()
    except EOFError:
        answer = ""

    if answer not in ("y", "yes"):
        log("Aborted by user.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def chat_completion(
    client: httpx.AsyncClient,
    model_id: str,
    messages: list[dict],
    *,
    tools: Optional[list] = None,
    response_format: Optional[dict] = None,
    max_tokens: int = 512,
    temperature: float = 0.0,
    stream: bool = False,
) -> dict:
    """Non-streaming chat completion. Returns {ok, content, tool_calls, usage, latency_ms, error}."""
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if response_format is not None:
        payload["response_format"] = response_format

    # Disable Venice system prompt noise for cleaner scoring
    payload["venice_parameters"] = {
        "include_venice_system_prompt": False,
        "disable_thinking": True,
    }

    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{VENICE_BASE}/chat/completions",
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        if resp.status_code >= 400:
            return {
                "ok": False,
                "content": "",
                "tool_calls": [],
                "usage": {},
                "latency_ms": latency_ms,
                "error": f"HTTP {resp.status_code}: {resp.text[:300]}",
            }
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return {
            "ok": True,
            "content": message.get("content") or "",
            "tool_calls": message.get("tool_calls") or [],
            "usage": data.get("usage") or {},
            "request_id": data.get("id") or data.get("request_id"),
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": False,
            "content": "",
            "tool_calls": [],
            "usage": {},
            "latency_ms": latency_ms,
            "error": str(exc),
        }


async def chat_completion_stream(
    client: httpx.AsyncClient,
    model_id: str,
    messages: list[dict],
    *,
    max_tokens: int = 64,
    temperature: float = 0.0,
) -> dict:
    """Streaming chat completion for TTFT measurement."""
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
        "venice_parameters": {
            "include_venice_system_prompt": False,
            "disable_thinking": True,
        },
    }

    t0 = time.perf_counter()
    ttft_ms: Optional[float] = None
    content_parts: list[str] = []
    usage: dict = {}
    request_id: Optional[str] = None

    try:
        async with client.stream(
            "POST",
            f"{VENICE_BASE}/chat/completions",
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                latency_ms = (time.perf_counter() - t0) * 1000
                return {
                    "ok": False,
                    "content": "",
                    "usage": {},
                    "latency_ms": latency_ms,
                    "ttft_ms": None,
                    "error": f"HTTP {resp.status_code}: {body[:300]!r}",
                }

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if chunk.get("usage"):
                    usage = chunk["usage"]

                # Capture request id from the first chunk if present
                if request_id is None:
                    request_id = chunk.get("id") or chunk.get("request_id")

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t0) * 1000
                    content_parts.append(piece)

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": True,
            "content": "".join(content_parts),
            "usage": usage,
            "request_id": request_id,
            "latency_ms": latency_ms,
            "ttft_ms": ttft_ms,
            "error": None,
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": False,
            "content": "",
            "usage": {},
            "latency_ms": latency_ms,
            "ttft_ms": ttft_ms,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Category aggregation helpers
# ---------------------------------------------------------------------------

def empty_category(skipped: bool = False, runs_skip: int = 0) -> dict:
    return {
        "runs_total": 0,
        "runs_success": 0,
        "runs_error": 0,
        "runs_skip": runs_skip,
        "skipped": skipped,
        "score_mean": None,
        "score_stdev": None,
        "score_effective": None,
        "latency_mean_ms": None,
        "latency_median_ms": None,
        "latency_p90_ms": None,
        "ttft_mean_ms": None,
        "tokens_per_sec_mean": None,
        "tokens_completion_mean": None,
        "tokens_prompt_mean": None,
    }


def aggregate_runs(
    scores: list[float],
    latencies: list[float],
    ttfts: list[float],
    tps: list[float],
    prompt_tokens: list[float],
    completion_tokens: list[float],
    runs_error: int,
    runs_skip: int = 0,
    skipped: bool = False,
    request_ids: Optional[list[str]] = None,
    sample_responses: Optional[list[str]] = None,
) -> dict:
    runs_success = len(scores)
    runs_total = runs_success + runs_error + runs_skip

    def _mean(xs: list[float]) -> Optional[float]:
        return statistics.mean(xs) if xs else None

    def _stdev(xs: list[float]) -> Optional[float]:
        return statistics.stdev(xs) if len(xs) >= 2 else (0.0 if xs else None)

    def _median(xs: list[float]) -> Optional[float]:
        return statistics.median(xs) if xs else None

    def _p90(xs: list[float]) -> Optional[float]:
        if not xs:
            return None
        ordered = sorted(xs)
        idx = max(0, math.ceil(0.9 * len(ordered)) - 1)
        return ordered[idx]

    score_mean = _mean(scores)
    return {
        "runs_total": runs_total,
        "runs_success": runs_success,
        "runs_error": runs_error,
        "runs_skip": runs_skip,
        "skipped": skipped,
        "score_mean": score_mean,
        "score_stdev": _stdev(scores),
        "score_effective": score_mean,
        "latency_mean_ms": _mean(latencies),
        "latency_median_ms": _median(latencies),
        "latency_p90_ms": _p90(latencies),
        "ttft_mean_ms": _mean(ttfts),
        "tokens_per_sec_mean": _mean(tps),
        "tokens_completion_mean": _mean(completion_tokens),
        "tokens_prompt_mean": _mean(prompt_tokens),
        "request_ids": [rid for rid in (request_ids or []) if rid],
        "sample_responses": [r for r in (sample_responses or []) if r is not None][:5],
    }


def _usage_tokens(usage: dict) -> tuple[float, float]:
    prompt = float(usage.get("prompt_tokens") or usage.get("promptTokens") or 0)
    completion = float(
        usage.get("completion_tokens") or usage.get("completionTokens") or 0
    )
    return prompt, completion


def _tps(completion: float, latency_ms: float) -> Optional[float]:
    if latency_ms <= 0 or completion <= 0:
        return None
    return completion / (latency_ms / 1000.0)


# ---------------------------------------------------------------------------
# T1 — Latency (streaming)
# ---------------------------------------------------------------------------

async def test_t1(
    client: httpx.AsyncClient,
    model_id: str,
    iterations: int,
) -> dict:
    scores: list[float] = []
    latencies: list[float] = []
    ttfts: list[float] = []
    tps_list: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    messages = [{"role": "user", "content": "Count from 1 to 5."}]

    for _ in range(iterations):
        result = await chat_completion_stream(
            client, model_id, messages, max_tokens=64
        )
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"] or not result["content"].strip():
            errors += 1
            continue

        latency = result["latency_ms"]
        ttft = result.get("ttft_ms")
        prompt, completion = _usage_tokens(result["usage"])
        # Fallback token estimate if usage missing
        if completion <= 0:
            completion = float(len(result["content"].split()))
        tps = _tps(completion, latency)

        latencies.append(latency)
        if ttft is not None:
            ttfts.append(ttft)
        if tps is not None:
            tps_list.append(tps)
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        sample_responses.append(result["content"])

        # Score: inverse latency, normalized. 200ms → ~1.0, 5000ms → ~0.04
        # Use TTFT when available (more meaningful), else total latency.
        ref = ttft if ttft is not None else latency
        score = min(1.0, max(0.0, 200.0 / max(ref, 1.0)))
        # Blend with throughput if available
        if tps is not None:
            tps_score = min(1.0, tps / 80.0)  # 80 tok/s ≈ perfect
            score = 0.6 * score + 0.4 * tps_score
        scores.append(score)

    return aggregate_runs(
        scores, latencies, ttfts, tps_list, prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# T2 — Tool Calling
# ---------------------------------------------------------------------------

WEATHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                    },
                },
                "required": ["city"],
            },
        },
    }
]


async def test_t2(
    client: httpx.AsyncClient,
    model_id: str,
    model_meta: dict,
    iterations: int,
) -> dict:
    if not model_meta["capabilities"]["supportsFunctionCalling"]:
        return empty_category(skipped=True, runs_skip=iterations)

    scores: list[float] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    messages = [
        {
            "role": "user",
            "content": "What's the weather in Tokyo right now? Use the get_weather tool.",
        }
    ]

    for _ in range(iterations):
        result = await chat_completion(
            client,
            model_id,
            messages,
            tools=WEATHER_TOOLS,
            max_tokens=256,
        )
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"]:
            errors += 1
            continue

        latencies.append(result["latency_ms"])
        prompt, completion = _usage_tokens(result["usage"])
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        sample_responses.append(json.dumps(result.get("tool_calls", []), ensure_ascii=False))

        score = 0.0
        tool_calls = result["tool_calls"]
        if tool_calls:
            tc = tool_calls[0]
            fn = tc.get("function") or {}
            name_ok = fn.get("name") == "get_weather"
            args_raw = fn.get("arguments") or ""
            args_ok = False
            city_ok = False
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                args_ok = isinstance(args, dict)
                if args_ok:
                    city = str(args.get("city", "")).lower()
                    city_ok = "tokyo" in city
            except (json.JSONDecodeError, TypeError):
                pass
            if name_ok and args_ok and city_ok:
                score = 1.0
            elif name_ok and args_ok:
                score = 0.7
            elif name_ok:
                score = 0.3
        scores.append(score)

    return aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# T3 — Structured Output
# ---------------------------------------------------------------------------

PERSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "person_record",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"},
            },
            "required": ["name", "age", "email"],
            "additionalProperties": False,
        },
    },
}

PERSON_PROMPT = (
    "Return a JSON object for a fictional person with exactly these fields: "
    "name (string), age (integer), email (string). "
    "No markdown, no explanation — only the JSON object."
)


def _validate_person_json(text: str) -> float:
    """Return 0.0–1.0 based on how well the response matches the person schema."""
    # Strip markdown fences if present
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    # Extract first JSON object
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return 0.0
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return 0.0
    if not isinstance(obj, dict):
        return 0.0

    score = 0.0
    if isinstance(obj.get("name"), str) and obj["name"].strip():
        score += 0.34
    if isinstance(obj.get("age"), (int, float)) and not isinstance(obj.get("age"), bool):
        score += 0.33
    email = obj.get("email")
    if isinstance(email, str) and "@" in email and "." in email:
        score += 0.33
    return min(1.0, score)


async def test_t3(
    client: httpx.AsyncClient,
    model_id: str,
    model_meta: dict,
    iterations: int,
) -> dict:
    scores: list[float] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    use_schema = model_meta["capabilities"]["supportsResponseSchema"]
    messages = [{"role": "user", "content": PERSON_PROMPT}]

    for _ in range(iterations):
        kwargs: dict[str, Any] = {"max_tokens": 256}
        if use_schema:
            kwargs["response_format"] = PERSON_SCHEMA

        result = await chat_completion(client, model_id, messages, **kwargs)
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"]:
            errors += 1
            continue

        latencies.append(result["latency_ms"])
        prompt, completion = _usage_tokens(result["usage"])
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        sample_responses.append(result["content"])
        scores.append(_validate_person_json(result["content"]))

    return aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# T4 — Instruction Following
# ---------------------------------------------------------------------------

T4_PROMPT = (
    "Reply with exactly 3 bullet points. "
    "Each bullet point must consist of a different emoji and nothing more. "
    "No introduction, no conclusion, no other text."
)

_BULLET_RE = re.compile(r"^[\s]*([•\-\*]|\d+\.)?\s*(\S)", re.MULTILINE)
# Broad emoji / symbol range
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F600-\U0001F64F"
    r"\U0001F680-\U0001F6FF\U00002600-\U000026FF]"
)


def _score_instruction_following(text: str) -> float:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return 0.0

    score = 0.0
    # Exactly 3 non-empty lines preferred
    if len(lines) == 3:
        score += 0.4
    elif abs(len(lines) - 3) == 1:
        score += 0.2

    emoji_starts = sum(1 for ln in lines if _EMOJI_RE.search(ln[:8] if len(ln) >= 1 else ln))
    if emoji_starts >= 3:
        score += 0.4
    elif emoji_starts >= 1:
        score += 0.15

    # Bullet-like structure
    bulletish = sum(
        1 for ln in lines
        if ln.startswith(("-", "*", "•")) or re.match(r"^\d+\.", ln) or _EMOJI_RE.match(ln)
    )
    if bulletish >= 3:
        score += 0.2
    elif bulletish >= 1:
        score += 0.1

    return min(1.0, score)


async def test_t4(
    client: httpx.AsyncClient,
    model_id: str,
    iterations: int,
) -> dict:
    scores: list[float] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    messages = [{"role": "user", "content": T4_PROMPT}]

    for _ in range(iterations):
        result = await chat_completion(client, model_id, messages, max_tokens=256)
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"]:
            errors += 1
            continue
        latencies.append(result["latency_ms"])
        prompt, completion = _usage_tokens(result["usage"])
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        sample_responses.append(result["content"])
        scores.append(_score_instruction_following(result["content"]))

    return aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# T5 — Reasoning Quality (river crossing)
# ---------------------------------------------------------------------------

T5_PROMPT = (
    "A farmer needs to cross a river with a fox, a chicken, and a bag of grain. "
    "His boat holds only himself and one item. The fox cannot be left alone with "
    "the chicken, and the chicken cannot be left alone with the grain. "
    "List the minimum sequence of crossings to get everything safely across. "
    "Number each step."
)


def _score_river_crossing(text: str) -> float:
    lower = text.lower()
    score = 0.0

    # Must mention bringing chicken first (classic solution starts with chicken)
    if "chicken" in lower:
        score += 0.2
    if "fox" in lower:
        score += 0.1
    if "grain" in lower or "corn" in lower:
        score += 0.1

    # Look for multi-step structure
    steps = re.findall(r"(?:^|\n)\s*(?:\d+[\.\):]|step\s*\d+|[-•*])", lower)
    if len(steps) >= 5:
        score += 0.3
    elif len(steps) >= 3:
        score += 0.15

    # Key insight: chicken goes first, farmer returns, etc.
    # Check for return trips (farmer comes back)
    returns = len(re.findall(r"return|back|comes?\s+back|goes?\s+back", lower))
    if returns >= 2:
        score += 0.2
    elif returns >= 1:
        score += 0.1

    # Penalty for leaving fox+chicken or chicken+grain alone incorrectly
    # (hard to detect; reward mentioning the constraints)
    if "cannot" in lower or "alone" in lower or "safe" in lower:
        score += 0.1

    return min(1.0, score)


async def test_t5(
    client: httpx.AsyncClient,
    model_id: str,
    iterations: int,
) -> dict:
    scores: list[float] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    messages = [{"role": "user", "content": T5_PROMPT}]

    for _ in range(iterations):
        result = await chat_completion(client, model_id, messages, max_tokens=512)
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"]:
            errors += 1
            continue
        latencies.append(result["latency_ms"])
        prompt, completion = _usage_tokens(result["usage"])
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        sample_responses.append(result["content"])
        scores.append(_score_river_crossing(result["content"]))

    return aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# T6 — Context Coherence (multi-turn)
# ---------------------------------------------------------------------------

async def test_t6(
    client: httpx.AsyncClient,
    model_id: str,
    iterations: int,
) -> dict:
    scores: list[float] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    for _ in range(iterations):
        history: list[dict] = []
        total_latency = 0.0
        total_prompt = 0.0
        total_completion = 0.0
        failed = False

        turns = [
            "My favorite color is blue and my pet's name is Whiskers.",
            "What is 12 + 30?",
            "What is my favorite color and my pet's name?",
        ]

        for turn in turns:
            history.append({"role": "user", "content": turn})
            result = await chat_completion(
                client, model_id, history, max_tokens=128
            )
            if result.get("request_id"):
                request_ids.append(result["request_id"])
            if not result["ok"]:
                failed = True
                break
            total_latency += result["latency_ms"]
            p, c = _usage_tokens(result["usage"])
            total_prompt += p
            total_completion += c
            history.append({"role": "assistant", "content": result["content"]})

        if failed or len(history) < 6:
            errors += 1
            continue

        latencies.append(total_latency)
        prompt_toks.append(total_prompt)
        completion_toks.append(total_completion)
        sample_responses.append(history[-1]["content"])

        final = history[-1]["content"].lower()
        score = 0.0
        if "blue" in final:
            score += 0.5
        if "whiskers" in final:
            score += 0.5
        scores.append(score)

    return aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# T7 — Consistency
# ---------------------------------------------------------------------------

T7_PROMPT = "What is 17 × 23? Reply with only the number."
T7_ANSWER = "391"


def _normalize_answer(text: str) -> str:
    # Extract first integer-like token
    m = re.search(r"-?\d+", text.replace(",", ""))
    return m.group(0) if m else text.strip().lower()


async def test_t7(
    client: httpx.AsyncClient,
    model_id: str,
    iterations: int,
) -> dict:
    answers: list[str] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    messages = [{"role": "user", "content": T7_PROMPT}]

    for _ in range(iterations):
        result = await chat_completion(client, model_id, messages, max_tokens=32)
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"]:
            errors += 1
            continue
        latencies.append(result["latency_ms"])
        prompt, completion = _usage_tokens(result["usage"])
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        answers.append(_normalize_answer(result["content"]))
        sample_responses.append(result["content"])

    if not answers:
        return aggregate_runs([], [], [], [], [], [], errors)

    # Per-iteration score: 1.0 if correct, 0.5 if consistent-but-wrong majority, 0.0 else
    # Also compute overall consistency
    correct_count = sum(1 for a in answers if a == T7_ANSWER)
    unique = set(answers)
    consistency = 1.0 - ((len(unique) - 1) / max(len(answers), 1))
    consistency = max(0.0, min(1.0, consistency))

    scores = []
    for a in answers:
        if a == T7_ANSWER:
            scores.append(1.0)
        else:
            # Partial credit for being consistent with the majority wrong answer
            scores.append(0.3 * consistency)

    # Blend accuracy into mean via the per-run scores; also boost if highly consistent+correct
    cat = aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )
    # Override score_mean to blend accuracy and consistency
    accuracy = correct_count / len(answers)
    blended = 0.7 * accuracy + 0.3 * consistency
    cat["score_mean"] = blended
    cat["score_effective"] = blended
    return cat


# ---------------------------------------------------------------------------
# T8 — Conciseness
# ---------------------------------------------------------------------------

T8_PROMPT = (
    "Explain what a hash table is in 50 words or fewer. "
    "Do not exceed 50 words."
)


def _score_conciseness(text: str) -> float:
    words = text.strip().split()
    n = len(words)
    if n == 0:
        return 0.0
    if n > 50:
        # Soft penalty: 51–70 words still partial credit
        if n <= 70:
            return max(0.0, 0.5 * (70 - n) / 20)
        return 0.0
    # Substantive: at least 5 words and mentions key concept
    lower = text.lower()
    has_concept = any(
        k in lower
        for k in ("hash", "key", "value", "lookup", "map", "bucket", "array", "index")
    )
    if n < 5:
        return 0.2
    if has_concept:
        return 1.0
    return 0.5


async def test_t8(
    client: httpx.AsyncClient,
    model_id: str,
    iterations: int,
) -> dict:
    scores: list[float] = []
    latencies: list[float] = []
    prompt_toks: list[float] = []
    completion_toks: list[float] = []
    request_ids: list[str] = []
    sample_responses: list[str] = []
    errors = 0

    messages = [{"role": "user", "content": T8_PROMPT}]

    for _ in range(iterations):
        result = await chat_completion(client, model_id, messages, max_tokens=128)
        if result.get("request_id"):
            request_ids.append(result["request_id"])
        if not result["ok"]:
            errors += 1
            continue
        latencies.append(result["latency_ms"])
        prompt, completion = _usage_tokens(result["usage"])
        prompt_toks.append(prompt)
        completion_toks.append(completion)
        sample_responses.append(result["content"])
        scores.append(_score_conciseness(result["content"]))

    return aggregate_runs(
        scores, latencies, [], [], prompt_toks, completion_toks, errors,
        request_ids=request_ids,
        sample_responses=sample_responses,
    )


# ---------------------------------------------------------------------------
# Per-model orchestration
# ---------------------------------------------------------------------------

async def run_test(
    client: httpx.AsyncClient,
    tid: str,
    model_id: str,
    model_meta: dict,
    iterations: int,
) -> dict:
    if tid == "T1":
        return await test_t1(client, model_id, iterations)
    if tid == "T2":
        return await test_t2(client, model_id, model_meta, iterations)
    if tid == "T3":
        return await test_t3(client, model_id, model_meta, iterations)
    if tid == "T4":
        return await test_t4(client, model_id, iterations)
    if tid == "T5":
        return await test_t5(client, model_id, iterations)
    if tid == "T6":
        return await test_t6(client, model_id, iterations)
    if tid == "T7":
        return await test_t7(client, model_id, iterations)
    if tid == "T8":
        return await test_t8(client, model_id, iterations)
    return empty_category(skipped=True)


def compute_composite(categories: dict[str, dict]) -> tuple[Optional[float], Optional[float]]:
    """Return (composite_score 0-100, data_coverage 0-1)."""
    weighted_sum = 0.0
    weight_total = 0.0
    eligible = 0
    successful = 0

    for tid, cat in categories.items():
        if cat.get("skipped"):
            continue
        eligible += 1
        if cat.get("runs_success", 0) >= 1:
            successful += 1
        score = cat.get("score_effective")
        if score is None:
            score = cat.get("score_mean")
        if score is None:
            continue
        w = WEIGHTS.get(tid, 0.1)
        weighted_sum += score * w
        weight_total += w

    if weight_total <= 0:
        return None, None

    composite = (weighted_sum / weight_total) * 100.0
    coverage = (successful / eligible) if eligible else None
    return composite, coverage


def compute_costs(categories: dict[str, dict], pricing_input: float, pricing_output: float) -> dict:
    """Compute list-price cost per category and model total from recorded token means.

    The token fields are per-run means, so scale by runs_success to get total
    tokens for the category.

    Returns a dict with:
      - categories: {tid: {"cost_usd": float, "cost_per_run_usd": float|null}}
      - total_cost_usd: float
      - total_cost_per_run_usd: float|null
    """
    enriched: dict[str, dict] = {}
    total_cost = 0.0
    total_runs = 0

    for tid, cat in categories.items():
        if cat.get("skipped") or cat.get("runs_success", 0) == 0:
            enriched[tid] = {"cost_usd": None, "cost_per_run_usd": None}
            continue

        prompt_mean = cat.get("tokens_prompt_mean") or 0.0
        completion_mean = cat.get("tokens_completion_mean") or 0.0
        runs = cat["runs_success"]

        # token fields are per-run means; scale to total tokens for the category
        total_prompt = float(prompt_mean) * runs
        total_completion = float(completion_mean) * runs

        cost = (
            (total_prompt * float(pricing_input))
            + (total_completion * float(pricing_output))
        ) / 1_000_000.0

        enriched[tid] = {
            "cost_usd": round(cost, 8),
            "cost_per_run_usd": round(cost / runs, 8) if runs else None,
        }
        total_cost += cost
        total_runs += runs

    return {
        "categories": enriched,
        "total_cost_usd": round(total_cost, 8),
        "total_cost_per_run_usd": round(total_cost / total_runs, 8) if total_runs else None,
    }


# DIEM is a 1:1 API credit against USD-denominated usage.
DIEM_USD_RATE = 1.0


async def reconcile_billed_costs(
    client: httpx.AsyncClient,
    models_results: list[dict],
    run_start: datetime,
    run_end: datetime,
) -> dict:
    """Query /billing/usage and match entries to recorded request IDs.

    Returns a mapping of request_id -> list of billing entries. Also updates
    each model result with actual_billed fields per category and model total.
    """
    # Collect all recorded request IDs grouped by model/category
    request_ids: set[str] = set()
    lookup: dict[str, tuple[str, str]] = {}  # request_id -> (model_id, tid)
    for model in models_results:
        model_id = model.get("model_id")
        for tid, cat in model.get("categories", {}).items():
            for rid in cat.get("request_ids", []):
                request_ids.add(rid)
                lookup[rid] = (model_id, tid)

    if not request_ids:
        log("No request IDs recorded; skipping billing reconciliation.")
        return {}

    diem_price = DIEM_USD_RATE

    # Widen the window: billing entries may be logged with a slight delay and
    # the endpoint may reject very narrow ranges.
    window_start = run_start - timedelta(minutes=5)
    window_end = run_end + timedelta(minutes=5)
    start_str = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    log(f"Reconciling billing for {len(request_ids)} request(s) from {start_str} to {end_str}…")
    matched: dict[str, list[dict]] = {}
    page = 1
    max_pages = 50

    while page <= max_pages:
        try:
            resp = await client.get(
                f"{VENICE_BASE}/billing/usage",
                params={
                    "startDate": start_str,
                    "endDate": end_str,
                    "limit": 500,
                    "sortOrder": "desc",
                    "page": page,
                },
            )
            if resp.status_code >= 400:
                body = resp.text[:500]
                log(f"WARNING: Billing usage returned {resp.status_code}: {body}")
                return {}
            payload = resp.json()
        except Exception as exc:
            log(f"WARNING: Billing reconciliation failed: {exc}")
            return {}

        entries = payload.get("data", [])
        if not entries:
            break

        for entry in entries:
            details = entry.get("inferenceDetails") or {}
            rid = details.get("requestId")
            if rid and rid in request_ids:
                matched.setdefault(rid, []).append(entry)

        pagination = payload.get("pagination", {})
        total_pages = int(
            pagination.get("totalPages", resp.headers.get("x-pagination-total-pages", 1))
        )
        if page >= total_pages:
            break
        page += 1
    else:
        log("WARNING: Billing reconciliation hit max page limit; results may be incomplete.")

    log(f"Matched {len(matched)} request(s) in billing usage.")

    # Aggregate matched amounts per model/category
    totals: dict[str, dict[str, dict[str, float]]] = {}
    for rid, entries in matched.items():
        model_id, tid = lookup[rid]
        model_totals = totals.setdefault(model_id, {})
        cat_totals = model_totals.setdefault(tid, {"usd": 0.0, "diem": 0.0, "bundled_credits": 0.0})
        for entry in entries:
            currency = (entry.get("currency") or "").upper()
            amount = float(entry.get("amount", 0))
            if currency == "USD":
                cat_totals["usd"] -= amount
            elif currency == "DIEM":
                cat_totals["diem"] -= amount
            elif currency in ("BUNDLED_CREDITS", "VCU"):
                cat_totals["bundled_credits"] -= amount

    # Update model results with actual billed costs
    for model in models_results:
        model_id = model.get("model_id")
        model_billed = {
            "categories": {},
            "total_usd": 0.0,
            "total_diem": 0.0,
            "total_bundled_credits": 0.0,
            "total_usd_equivalent": 0.0,
            "diem_price_usd": diem_price,
        }
        for tid, cat in model.get("categories", {}).items():
            if cat.get("skipped") or cat.get("runs_success", 0) == 0:
                model_billed["categories"][tid] = {
                    "billed_usd": None,
                    "billed_diem": None,
                    "billed_bundled_credits": None,
                    "billed_usd_equivalent": None,
                }
                continue
            bt = totals.get(model_id, {}).get(tid, {"usd": 0.0, "diem": 0.0, "bundled_credits": 0.0})
            runs = cat["runs_success"]
            usd_equiv = bt["usd"] + (bt["diem"] * (diem_price or 0.0))
            model_billed["categories"][tid] = {
                "billed_usd": round(bt["usd"], 8) if bt["usd"] else None,
                "billed_diem": round(bt["diem"], 8) if bt["diem"] else None,
                "billed_bundled_credits": round(bt["bundled_credits"], 8) if bt["bundled_credits"] else None,
                "billed_usd_equivalent": round(usd_equiv, 8) if usd_equiv else None,
                "billed_per_run_usd_equivalent": round(usd_equiv / runs, 8) if usd_equiv else None,
            }
            model_billed["total_usd"] += bt["usd"]
            model_billed["total_diem"] += bt["diem"]
            model_billed["total_bundled_credits"] += bt["bundled_credits"]
            model_billed["total_usd_equivalent"] += usd_equiv

        model["actual_billed"] = model_billed

    return matched


async def run_model_benchmark(
    client: httpx.AsyncClient,
    model: dict,
    tests: list[str],
    iterations: int,
    semaphore: asyncio.Semaphore,
) -> dict:
    model_meta = extract_model_meta(model)
    model_id = model_meta["id"]

    async with semaphore:
        log(f"→ Starting model: {model_id}")
        categories: dict[str, dict] = {}
        for tid in tests:
            log(f"  [{model_id}] running {tid}…")
            try:
                cat = await run_test(client, tid, model_id, model_meta, iterations)
            except Exception as exc:
                log(f"  [{model_id}] {tid} FAILED: {exc}")
                cat = empty_category()
                cat["runs_total"] = iterations
                cat["runs_error"] = iterations
            categories[tid] = cat
            if cat.get("skipped"):
                log(f"  [{model_id}] {tid}: skipped")
            else:
                sm = cat.get("score_mean")
                sm_s = f"{sm:.3f}" if sm is not None else "n/a"
                log(
                    f"  [{model_id}] {tid}: score={sm_s} "
                    f"ok={cat['runs_success']}/{cat['runs_total']} "
                    f"err={cat['runs_error']}"
                )

        composite, coverage = compute_composite(categories)
        costs = compute_costs(
            categories,
            pricing_input=model_meta.get("pricing_input_usd") or 0.0,
            pricing_output=model_meta.get("pricing_output_usd") or 0.0,
        )
        cs = f"{composite:.1f}" if composite is not None else "n/a"
        cost_s = f"${costs['total_cost_usd']:.4f}" if costs.get("total_cost_usd") is not None else "n/a"
        log(f"← Finished model: {model_id} (composite={cs}, cost={cost_s})")

        return {
            "model_id": model_id,
            "model_meta": model_meta,
            "categories": categories,
            "costs": costs,
            "composite_score": composite,
            "data_coverage": coverage,
        }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_results(output_dir: Path, models_results: list[dict]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"benchmark_{stamp}.json"

    # Aggregate list-price and actual billed costs across all models
    total_list_cost = sum(
        (m.get("costs") or {}).get("total_cost_usd") or 0.0
        for m in models_results
    )
    total_actual_billed_usd = sum(
        (m.get("actual_billed") or {}).get("total_usd") or 0.0
        for m in models_results
    )
    total_actual_billed_usd_equiv = sum(
        (m.get("actual_billed") or {}).get("total_usd_equivalent") or 0.0
        for m in models_results
    )

    payload = {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "model_count": len(models_results),
        "total_cost_usd": round(total_list_cost, 8),
        "total_actual_billed_usd": round(total_actual_billed_usd, 8) if total_actual_billed_usd else None,
        "total_actual_billed_usd_equivalent": round(total_actual_billed_usd_equiv, 8) if total_actual_billed_usd_equiv else None,
        "models": models_results,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    log(f"Wrote results: {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Venice text model benchmark (T1–T8)")
    p.add_argument("--api-key", required=True, help="Venice API key")
    p.add_argument(
        "--admin-key",
        default=None,
        help="Venice admin key (required for /billing/usage reconciliation)",
    )
    p.add_argument("--iterations", type=int, default=10)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--privacy",
        choices=["both", "private", "anonymized"],
        default="both",
    )
    p.add_argument("--output", required=True, help="Directory for benchmark_*.json")
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive cost confirmation",
    )
    p.add_argument(
        "--no-infographic",
        action="store_true",
        help="No-op (infographic is generated by the backend)",
    )
    p.add_argument(
        "--tests",
        default=None,
        help="Comma-separated test IDs (default: all T1–T8)",
    )
    p.add_argument(
        "--models",
        default=None,
        help="Comma-separated model IDs (default: all qualifying)",
    )
    return p.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    tests = ALL_TESTS
    if args.tests:
        tests = [t.strip().upper() for t in args.tests.split(",") if t.strip()]
        unknown = [t for t in tests if t not in ALL_TESTS]
        if unknown:
            log(f"ERROR: Unknown tests: {unknown}. Valid: {ALL_TESTS}")
            return 1
        if not tests:
            log("ERROR: No tests selected")
            return 1

    requested_models: Optional[list[str]] = None
    if args.models:
        requested_models = [m.strip() for m in args.models.split(",") if m.strip()]
        if not requested_models:
            log("ERROR: --models provided but empty")
            return 1

    headers = {
        "Authorization": f"Bearer {args.api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(headers=headers, timeout=REQUEST_TIMEOUT_S) as client:
        log("Fetching qualifying models…")
        try:
            all_models = await fetch_qualifying_models(client, args.privacy)
        except Exception as exc:
            log(f"ERROR: Failed to fetch models: {exc}")
            return 1

        log(f"Found {len(all_models)} qualifying models (privacy={args.privacy})")

        if requested_models is not None:
            by_id = {m.get("id"): m for m in all_models}
            selected = []
            missing = []
            for mid in requested_models:
                if mid in by_id:
                    selected.append(by_id[mid])
                else:
                    missing.append(mid)
            if missing:
                log(f"WARNING: Models not in qualifying set (will skip): {missing}")
            models = selected
        else:
            models = all_models

        if not models:
            log("ERROR: No models to benchmark")
            return 1

        log(f"Selected {len(models)} model(s): {', '.join(m.get('id','?') for m in models)}")

        run_start = datetime.now(timezone.utc)

        # Cost estimate + confirmation gate
        confirm_or_exit(
            models=models,
            tests=tests,
            iterations=args.iterations,
            workers=args.workers,
            yes=args.yes,
            output_dir=Path(args.output),
        )

        semaphore = asyncio.Semaphore(max(1, args.workers))
        total = len(models)
        completed = 0
        results: list[dict] = []

        # Run models with bounded concurrency
        async def _wrap(model: dict) -> dict:
            nonlocal completed
            result = await run_model_benchmark(
                client, model, tests, args.iterations, semaphore
            )
            completed += 1
            progress(completed, total, result["model_id"])
            return result

        tasks = [asyncio.create_task(_wrap(m)) for m in models]
        for coro in asyncio.as_completed(tasks):
            try:
                results.append(await coro)
            except Exception as exc:
                log(f"ERROR: Model task crashed: {exc}")
                completed += 1
                progress(completed, total)

        # Stable sort by model_id for deterministic output
        results.sort(key=lambda r: r.get("model_id", ""))

        # Reconcile actual billed costs if admin key provided
        if args.admin_key:
            run_end = datetime.now(timezone.utc)
            await reconcile_billed_costs(
                client=httpx.AsyncClient(
                    headers={
                        "Authorization": f"Bearer {args.admin_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=REQUEST_TIMEOUT_S,
                ),
                models_results=results,
                run_start=run_start,
                run_end=run_end,
            )
            # Re-write results with actual_billed fields
            out_path = write_results(Path(args.output), results)
        else:
            out_path = write_results(Path(args.output), results)

        log(f"Done. {len(results)} model(s) written to {out_path.name}")
        return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        log("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

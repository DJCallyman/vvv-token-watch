"""
benchmark_suite.py — All 8 test functions for the Venice text model benchmark.

Each test function accepts:
    client   : BenchmarkClient instance (handles auth, retry, streaming)
    model_id : str
    caps     : dict of model_spec.capabilities

Each test function returns a list of RunResult dicts (one per iteration).

RunResult schema:
    {
        "status"           : "success" | "error" | "timeout" | "skip",
        "score"            : float 0.0-1.0 (None if skip/error),
        "latency_ms"       : float | None,
        "ttft_ms"          : float | None,
        "tokens_prompt"    : int | None,
        "tokens_completion": int | None,
        "tokens_total"     : int | None,
        "tokens_per_sec"   : float | None,
        "finish_reason"    : str | None,
        "error"            : str | None,
        "raw_excerpt"      : str | None,  # first 500 chars of response content
    }
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from benchmark_models import BenchmarkClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_result(**overrides) -> dict:
    base = {
        "status": "error",
        "score": None,
        "latency_ms": None,
        "ttft_ms": None,
        "tokens_prompt": None,
        "tokens_completion": None,
        "tokens_total": None,
        "tokens_per_sec": None,
        "finish_reason": None,
        "error": None,
        "raw_excerpt": None,
    }
    base.update(overrides)
    return base


def _skip(reason: str = "not supported") -> dict:
    return _empty_result(status="skip", error=reason)


def _extract_usage(data: dict) -> dict:
    usage = data.get("usage") or {}
    pt = usage.get("prompt_tokens")
    ct = usage.get("completion_tokens")
    tt = usage.get("total_tokens")
    return {"tokens_prompt": pt, "tokens_completion": ct, "tokens_total": tt}


def _tokens_per_sec(tokens_completion, latency_ms):
    if tokens_completion and latency_ms and latency_ms > 0:
        return round(tokens_completion / (latency_ms / 1000.0), 2)
    return None


# ---------------------------------------------------------------------------
# T1 — Latency
# ---------------------------------------------------------------------------

def test_latency(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    """
    Stream a trivial prompt and record TTFT + total latency + tokens/sec.
    Score is deferred to aggregation (normalized across all models).
    """
    results = []
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "What is 2+2? Answer with a single number."}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_completion_tokens": 20,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    for _ in range(iterations):
        r = _empty_result()
        t_start = time.perf_counter()
        ttft_ms = None
        content_chunks = []
        final_usage = {}
        finish_reason = None

        try:
            with client.post_stream("/chat/completions", payload) as resp:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Usage chunk (stream_options)
                    if "usage" in chunk and not chunk.get("choices"):
                        final_usage = chunk["usage"]
                        continue

                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        token_text = delta.get("content", "")
                        if token_text and ttft_ms is None:
                            ttft_ms = (time.perf_counter() - t_start) * 1000
                        content_chunks.append(token_text)
                        if choices[0].get("finish_reason"):
                            finish_reason = choices[0]["finish_reason"]

            t_end = time.perf_counter()
            latency_ms = (t_end - t_start) * 1000
            content = "".join(content_chunks)

            pt = final_usage.get("prompt_tokens")
            ct = final_usage.get("completion_tokens")
            tt = final_usage.get("total_tokens")

            r = _empty_result(
                status="success",
                score=None,  # normalized at aggregation time
                latency_ms=round(latency_ms, 2),
                ttft_ms=round(ttft_ms, 2) if ttft_ms else None,
                tokens_prompt=pt,
                tokens_completion=ct,
                tokens_total=tt,
                tokens_per_sec=_tokens_per_sec(ct, latency_ms),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
            )
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            r = _empty_result(status=status, error=str(e))

        results.append(r)
        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# T2 — Tool Calling
# ---------------------------------------------------------------------------

_TRAVEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_travel_dates",
            "description": "Set the departure and return dates for the trip",
            "parameters": {
                "type": "object",
                "properties": {
                    "departure_date": {"type": "string", "description": "ISO-8601 departure date"},
                    "return_date": {"type": "string", "description": "ISO-8601 return date"},
                },
                "required": ["departure_date", "return_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_destination",
            "description": "Set the travel destination",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "country": {"type": "string"},
                    "airport_code": {"type": "string"},
                },
                "required": ["city", "country"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_traveler_info",
            "description": "Record traveler details",
            "parameters": {
                "type": "object",
                "properties": {
                    "adults": {"type": "integer"},
                    "children": {"type": "integer"},
                    "requires_wheelchair": {"type": "boolean"},
                },
                "required": ["adults"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_budget",
            "description": "Set the total trip budget in USD",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount_usd": {"type": "number"},
                    "budget_level": {"type": "string", "enum": ["budget", "mid-range", "luxury"]},
                },
                "required": ["amount_usd", "budget_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_priorities",
            "description": "Record what the traveler values most",
            "parameters": {
                "type": "object",
                "properties": {
                    "priorities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of travel priorities e.g. food, culture, relaxation",
                    }
                },
                "required": ["priorities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_hotels",
            "description": "Suggest hotel options given destination and budget",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "budget_level": {"type": "string", "enum": ["budget", "mid-range", "luxury"]},
                    "num_suggestions": {"type": "integer", "default": 3},
                },
                "required": ["destination", "budget_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_activities",
            "description": "Suggest activities based on destination and priorities",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "priorities": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["destination"],
            },
        },
    },
]

_TRAVEL_USER_MSG = (
    "I'm planning a trip from New York to Tokyo, Japan (NRT). "
    "I want to leave on June 10th 2026 and come back on June 24th. "
    "It'll be 2 adults and 1 child. Our total budget is around $8,000 — mid-range. "
    "We love food, culture, and photography. Please start organizing our trip by calling the appropriate tool."
)

_TRAVEL_SYSTEM_MSG = (
    "You are a travel planning assistant. "
    "You MUST respond by calling exactly one of the provided tools. "
    "Do not write any text — only call a tool."
)


def test_tool_calling(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    if not caps.get("supportsFunctionCalling"):
        return [_skip("model does not support function calling")] * iterations

    results = []
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": _TRAVEL_SYSTEM_MSG},
            {"role": "user", "content": _TRAVEL_USER_MSG},
        ],
        "tools": _TRAVEL_TOOLS,
        "tool_choice": "auto",
        "max_completion_tokens": 300,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    valid_tool_names = {t["function"]["name"] for t in _TRAVEL_TOOLS}

    for _ in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message", {})
            finish_reason = choice.get("finish_reason")
            tool_calls = msg.get("tool_calls") or []

            score = 0.0
            called_valid = False
            args_valid = False

            if tool_calls:
                tc = tool_calls[0]
                fn_name = tc.get("function", {}).get("name", "")
                fn_args = tc.get("function", {}).get("arguments", "")
                called_valid = fn_name in valid_tool_names
                try:
                    json.loads(fn_args)
                    args_valid = True
                except (json.JSONDecodeError, TypeError):
                    args_valid = False
                # Score: 0.5 for calling any valid tool, +0.5 for valid JSON args
                score = (0.5 if called_valid else 0.0) + (0.5 if args_valid else 0.0)

            usage = _extract_usage(data)
            results.append(_empty_result(
                status="success",
                score=score,
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=json.dumps(tool_calls)[:500] if tool_calls else msg.get("content", "")[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))

        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# T3 — Structured Output
# ---------------------------------------------------------------------------

_EXTRACT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "person_record",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"},
                "occupation": {"type": "string"},
                "email": {"type": ["string", "null"]},
            },
            "required": ["full_name", "age", "city", "occupation", "email"],
            "additionalProperties": False,
        },
    },
}

_EXTRACT_TEXT = (
    "Dr. Maria Chen, 42, is a software architect living in Austin, Texas. "
    "She has been working at a fintech startup for the past five years. "
    "Her contact email is mchen@example.com."
)

_EXPECTED_EXTRACT = {
    "full_name": str,
    "age": int,
    "city": str,
    "occupation": str,
    "email": (str, type(None)),
}


def test_structured_output(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    results = []
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": "Extract structured information from the user's text. Return only the JSON object.",
            },
            {"role": "user", "content": f"Extract the person details from this text:\n\n{_EXTRACT_TEXT}"},
        ],
        "response_format": _EXTRACT_SCHEMA,
        "max_completion_tokens": 200,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    for _ in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "")
            finish_reason = choice.get("finish_reason")
            usage = _extract_usage(data)

            score = 0.0
            try:
                parsed = json.loads(content)
                fields_correct = sum(
                    1 for field, ftype in _EXPECTED_EXTRACT.items()
                    if field in parsed and isinstance(parsed[field], ftype)
                )
                score = fields_correct / len(_EXPECTED_EXTRACT)
            except (json.JSONDecodeError, TypeError):
                score = 0.0

            results.append(_empty_result(
                status="success",
                score=round(score, 4),
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))

        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# T4 — Instruction Following
# ---------------------------------------------------------------------------

def test_instruction_following(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    results = []
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You must respond with ONLY a single integer. "
                    "No words, punctuation, spaces, or any other text. "
                    "Just the bare integer digit(s)."
                ),
            },
            {"role": "user", "content": "How many days are in a week?"},
        ],
        "max_completion_tokens": 10,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    for _ in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "").strip()
            finish_reason = choice.get("finish_reason")
            usage = _extract_usage(data)

            # Score 1.0 if response is exactly "7", 0.5 if it's a bare integer, 0 otherwise
            if content == "7":
                score = 1.0
            elif re.fullmatch(r"\d+", content):
                score = 0.5  # followed instruction to use only integer, but wrong value
            else:
                score = 0.0

            results.append(_empty_result(
                status="success",
                score=score,
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))

        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# T5 — Reasoning Quality
# ---------------------------------------------------------------------------

# Classic missionaries and cannibals variant — answer is 11 crossings minimum.
_REASONING_PROBLEM = """
A farmer needs to transport a fox, a chicken, and a bag of grain across a river.
The boat can only carry the farmer and ONE other item at a time.
Rules:
- Left alone, the fox will eat the chicken.
- Left alone, the chicken will eat the grain.
- The farmer must be present to prevent either from eating the other.

What is the minimum number of one-way river crossings needed to safely move
all three items to the other side? Answer with ONLY the integer (e.g., 7).
""".strip()

_REASONING_ANSWER = 7


def test_reasoning_quality(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    results = []

    extra = {}
    if caps.get("supportsReasoning"):
        extra["reasoning"] = {"effort": "high"}
    if caps.get("supportsReasoningEffort") and not caps.get("supportsReasoning"):
        # Some models use a different flag
        extra["reasoning"] = {"effort": "high"}

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful logical thinker. "
                    "Solve the problem step by step, then state ONLY the final integer answer on the last line."
                ),
            },
            {"role": "user", "content": _REASONING_PROBLEM},
        ],
        "max_completion_tokens": 1024,
        "venice_parameters": {
            "include_venice_system_prompt": False,
            "strip_thinking_response": True,
        },
        **extra,
    }

    for _ in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "").strip()
            finish_reason = choice.get("finish_reason")
            usage = _extract_usage(data)

            # Extract the last integer from the response
            numbers = re.findall(r"\b\d+\b", content)
            last_number = int(numbers[-1]) if numbers else None
            score = 1.0 if last_number == _REASONING_ANSWER else 0.0

            results.append(_empty_result(
                status="success",
                score=score,
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))

        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# T6 — Context Coherence
# ---------------------------------------------------------------------------

_UNIQUE_FACT = "Zephyr"  # cat name planted in turn 1

_COHERENCE_MESSAGES_TEMPLATE = [
    {"role": "user", "content": f"Hi! I have a cat named {_UNIQUE_FACT}. She loves sleeping in sunbeams."},
    {"role": "assistant", "content": "That sounds lovely! Cats do love warm spots. Does Zephyr have any other favourite places?"},
    {"role": "user", "content": "She likes the kitchen windowsill too. By the way, what is my cat's name?"},
]


def test_context_coherence(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    results = []
    payload = {
        "model": model_id,
        "messages": _COHERENCE_MESSAGES_TEMPLATE,
        "max_completion_tokens": 100,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    for _ in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "")
            finish_reason = choice.get("finish_reason")
            usage = _extract_usage(data)

            # 1.0 if "Zephyr" appears (case-insensitive), 0 otherwise
            score = 1.0 if _UNIQUE_FACT.lower() in content.lower() else 0.0

            results.append(_empty_result(
                status="success",
                score=score,
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))

        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# T7 — Consistency
# ---------------------------------------------------------------------------

_CONSISTENCY_PROMPT = "Name one primary color. Answer with a single word only."


def test_consistency(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    """
    Run iterations of the same prompt; score = 1 - (unique_responses / iterations).
    High score means the model gives the same answer every time.
    Reuses T4-style latency tracking; stores all responses for variance computation.
    """
    results = []
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": "Answer with exactly one word. No punctuation, no explanation.",
            },
            {"role": "user", "content": _CONSISTENCY_PROMPT},
        ],
        "max_completion_tokens": 10,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    responses = []

    for i in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "").strip().lower()
            finish_reason = choice.get("finish_reason")
            usage = _extract_usage(data)
            responses.append(content)

            # Score assigned after all iterations; use placeholder
            results.append(_empty_result(
                status="success",
                score=None,  # filled in after loop
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))
            responses.append(None)

        time.sleep(0.5)

    # Compute consistency score across all successful runs
    valid_responses = [r for r in responses if r is not None]
    if valid_responses:
        unique_count = len(set(valid_responses))
        consistency_score = round(1.0 - (unique_count - 1) / max(len(valid_responses), 1), 4)
        consistency_score = max(0.0, min(1.0, consistency_score))
    else:
        consistency_score = None

    # Back-fill score on successful results
    for r in results:
        if r["status"] == "success":
            r["score"] = consistency_score

    return results


# ---------------------------------------------------------------------------
# T8 — Conciseness
# ---------------------------------------------------------------------------

def test_conciseness(client: "BenchmarkClient", model_id: str, caps: dict, iterations: int) -> list[dict]:
    """
    System demands ≤10-word answer. Score penalised linearly for each word over limit.
    Score = max(0, 1 - (word_count - 10) / 10)
    """
    results = []
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Be extremely brief. Answer in 10 words or fewer. "
                    "No padding, no greetings, no explanation."
                ),
            },
            {"role": "user", "content": "What is the capital of France?"},
        ],
        "max_completion_tokens": 50,
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    for _ in range(iterations):
        t_start = time.perf_counter()
        try:
            data = client.post_json("/chat/completions", payload)
            latency_ms = (time.perf_counter() - t_start) * 1000

            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "").strip()
            finish_reason = choice.get("finish_reason")
            usage = _extract_usage(data)

            word_count = len(content.split())
            score = max(0.0, 1.0 - (word_count - 10) / 10.0)
            score = round(min(1.0, score), 4)

            results.append(_empty_result(
                status="success",
                score=score,
                latency_ms=round(latency_ms, 2),
                finish_reason=finish_reason,
                raw_excerpt=content[:500],
                **usage,
                tokens_per_sec=_tokens_per_sec(usage["tokens_completion"], latency_ms),
            ))
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            results.append(_empty_result(status=status, error=str(e)))

        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_TESTS = {
    "T1": ("Latency", test_latency),
    "T2": ("Tool Calling", test_tool_calling),
    "T3": ("Structured Output", test_structured_output),
    "T4": ("Instruction Following", test_instruction_following),
    "T5": ("Reasoning Quality", test_reasoning_quality),
    "T6": ("Context Coherence", test_context_coherence),
    "T7": ("Consistency", test_consistency),
    "T8": ("Conciseness", test_conciseness),
}

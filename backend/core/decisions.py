"""Typed decision evaluation via Venice's Jev /decisions endpoint (beta).

Jev is a System One decision model: instead of generating prose it evaluates a
``state`` against questions with predefined answer types and returns
machine-ready judgments (noul yes/no probability, choice with distribution,
score with legend). See https://docs.venice.ai/guides/features/decisions.

This module is intentionally generic: app-specific question builders live with
their callers (e.g. ``backend.api.routes.insights``) so other features (alerts,
assistant routing) can reuse the plumbing here.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

import httpx
from pydantic import BaseModel, Field, ValidationError

from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)

JEV_MODEL = "jev-latest"

# Noul answer: binary judgment as a probability from 0 (no) to 1 (yes).
# No separate confidence field — the probability itself carries certainty.
class DecisionNoul(BaseModel):
    type: str = "noul"
    noul: float = Field(..., ge=0.0, le=1.0)

# Choice answer: picked option, per-option probabilities, and confidence.
class DecisionChoice(BaseModel):
    type: str = "choice"
    choice: str
    probabilities: Dict[str, float]
    confidence: float = Field(..., ge=0.0, le=1.0)

# Score answer: probability-weighted position on an ordered rubric; can fall
# between levels. Keys in legend/probabilities are level indexes as strings.
class DecisionScore(BaseModel):
    type: str = "score"
    score: float
    legend: Dict[str, str]
    probabilities: Dict[str, float]
    confidence: float = Field(..., ge=0.0, le=1.0)

DecisionAnswer = DecisionNoul | DecisionChoice | DecisionScore

class DecisionUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

class DecisionsResult(BaseModel):
    model: str
    answers: Dict[str, DecisionAnswer]
    usage: DecisionUsage

def _normalize_answer(raw: Any) -> Optional[DecisionAnswer]:
    """Coerce one raw answer object into a typed model, or None if malformed."""
    if not isinstance(raw, dict):
        return None
    answer_type = raw.get("type")
    try:
        if answer_type == "noul":
            return DecisionNoul(type="noul", noul=float(raw.get("noul", 0.0)))
        if answer_type == "choice":
            return DecisionChoice(
                type="choice",
                choice=str(raw.get("choice", "")),
                probabilities={str(k): float(v) for k, v in (raw.get("probabilities") or {}).items()},
                confidence=float(raw.get("confidence", 0.0)),
            )
        if answer_type == "score":
            return DecisionScore(
                type="score",
                score=float(raw.get("score", 0.0)),
                legend={str(k): str(v) for k, v in (raw.get("legend") or {}).items()},
                probabilities={str(k): float(v) for k, v in (raw.get("probabilities") or {}).items()},
                confidence=float(raw.get("confidence", 0.0)),
            )
    except (TypeError, ValueError):
        return None
    return None

def normalize_decisions_response(payload: Any) -> Optional[DecisionsResult]:
    """Normalize a raw /decisions response. Returns None when malformed."""
    if not isinstance(payload, dict):
        return None
    raw_answers = payload.get("answers")
    if not isinstance(raw_answers, dict) or not raw_answers:
        return None
    answers: Dict[str, DecisionAnswer] = {}
    for question_id, raw in raw_answers.items():
        normalized = _normalize_answer(raw)
        if normalized is not None:
            answers[str(question_id)] = normalized
    if not answers:
        return None
    raw_usage = payload.get("usage") or {}
    try:
        usage = DecisionUsage(
            input_tokens=int(raw_usage.get("input_tokens", 0)),
            output_tokens=int(raw_usage.get("output_tokens", 0)),
        )
    except (TypeError, ValueError):
        usage = DecisionUsage()
    return DecisionsResult(
        model=str(payload.get("model") or JEV_MODEL),
        answers=answers,
        usage=usage,
    )

RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 1.5

async def evaluate_decisions(
    client: VeniceAPIClient,
    state: Any,
    questions: Dict[str, Any],
    model: str = JEV_MODEL,
    timeout: float = 45.0,
) -> Optional[DecisionsResult]:
    """Call POST /decisions and return a normalized result.

    Retries once with a short backoff on 5xx server errors — the beta endpoint
    has shown transient "Inference processing failed" 500s. Network/timeouts
    are already retried by the underlying client; other failures return None.
    """
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            payload = await client.post_json(
                "/decisions",
                data={"model": model, "state": state, "questions": questions},
                timeout=timeout,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and status >= 500 and attempt < RETRY_ATTEMPTS:
                logger.warning(
                    "Decisions API returned %s (attempt %s/%s), retrying in %.1fs",
                    status, attempt, RETRY_ATTEMPTS, RETRY_BACKOFF_SECONDS,
                )
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue
            logger.warning("Decisions API call failed: %s", exc)
            return None
        except (httpx.TimeoutException, httpx.ConnectError, ValueError) as exc:
            logger.warning("Decisions API call failed: %s", exc)
            return None
        normalized = normalize_decisions_response(payload)
        if normalized is None:
            logger.warning("Decisions API returned an unexpected payload shape")
        return normalized
    return None  # pragma: no cover - loop always returns

async def safe_evaluate_decisions(
    client: VeniceAPIClient,
    state: Any,
    questions: Dict[str, Any],
    model: str = JEV_MODEL,
    timeout: float = 45.0,
) -> Tuple[Optional[DecisionsResult], Optional[str]]:
    """Evaluate with full degradation: any failure becomes (None, reason).

    Returns a ``(result, error)`` tuple so callers can surface why typed
    judgments are unavailable (e.g. in a UI status hint). The error string is
    a short, stable description — never raw exception internals.
    """
    try:
        result = await evaluate_decisions(client, state, questions, model=model, timeout=timeout)
    except Exception as exc:  # pragma: no cover - defensive breadth
        logger.warning("Decisions evaluation raised unexpectedly: %s", exc)
        return None, "unexpected_error"
    if result is not None:
        return result, None
    return None, "decisions_unavailable"

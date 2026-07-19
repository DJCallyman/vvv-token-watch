"""FastAPI routes for the benchmark feature.

Endpoints:
  GET  /api/benchmark/runs                — list available result files
  GET  /api/benchmark/runs/{run_id}       — get full results for a run
  GET  /api/benchmark/models              — list qualifying Venice text models
  POST /api/benchmark/start               — start a benchmark subprocess
  GET  /api/benchmark/stream/{job_id}     — SSE stream of job stdout
  GET  /api/benchmark/status/{job_id}     — check job status
  POST /api/benchmark/infographic/{run_id} — generate infographic via Venice image API
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from backend.core.venice_api_client import VeniceAPIClient
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from backend.models.schemas import (
    BenchmarkEstimateParams,
    BenchmarkEstimateResponse,
    BenchmarkStartParams,
)
from backend.limiter import limiter
from sse_starlette.sse import EventSourceResponse

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

# Rough token estimates for cost projection (prompt / completion per call).
# Prompt estimates are kept in sync with scripts/benchmark_models.py.
# Completion estimates prefer historical observed means from prior runs.
_TOKEN_ESTIMATES = {
    "T1": (20, 30),
    "T2": (80, 60),
    "T3": (60, 80),
    "T4": (50, 60),
    "T5": (120, 200),
    "T6": (150, 40),  # multi-turn: ~3 messages
    "T7": (25, 15),
    "T8": (40, 60),
}
_ALL_TESTS = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]

# Models that always generate reasoning tokens regardless of max_tokens or
# reasoning controls. Estimates for these models should use historical averages.
_ALWAYS_REASONING_MODELS = {
    "grok-build-0-1",
    "grok-4-3",
    "grok-4-5",
    "grok-4-20",
    "grok-4-20-multi-agent",
}


def _load_historical_completion_estimates(results_dir: Path) -> dict[str, dict[str, float]]:
    """Load observed completion token means per (model_id, test_id) from prior runs."""
    estimates: dict[str, dict[str, float]] = {}
    for path in sorted(results_dir.glob("benchmark_*.json"), key=lambda p: p.stat().st_mtime):
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
                model_est[tid] = float(mean)
    return estimates

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# backend/api/routes/benchmark.py → repo root is 4 levels up
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_BENCHMARK_SCRIPT = _REPO_ROOT / "scripts" / "benchmark_models.py"
_VENICE_BASE = settings.VENICE_API_BASE_URL


def _results_dir() -> Path:
    d = Path(settings.BENCHMARK_RESULTS_DIR)
    if not d.is_absolute():
        d = _REPO_ROOT / d
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------

_jobs: dict[str, dict] = {}
# {
#   job_id: {
#     "proc": asyncio.subprocess.Process,
#     "status": "running"|"done"|"failed",
#     "run_id": str | None,
#     "started_at": float,
#     "logs": list[dict],          # {type, line, ts}
#     "progress": dict | None,     # {done, total, model_id}
#     "error": str | None,
#     "reader_task": asyncio.Task | None,
#   }
# }

_MAX_CONCURRENT_JOBS = 1
_JOB_TTL_SECONDS = 3600
_MAX_LOG_LINES = 2000


async def terminate_all_jobs():
    """Terminate all running benchmark jobs. Called during application shutdown."""
    for job_id, job in list(_jobs.items()):
        task = job.get("reader_task")
        if task is not None and not task.done():
            task.cancel()
        proc = job.get("proc")
        if proc is not None and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            except Exception as exc:
                logger.error("Error terminating benchmark job %s: %s", job_id, exc)


def _cleanup_stale_jobs():
    """Evict completed jobs older than the TTL to prevent unbounded growth."""
    now = time.time()
    stale = [
        job_id for job_id, job in _jobs.items()
        if job.get("status") in ("done", "failed")
        and now - job.get("started_at", now) > _JOB_TTL_SECONDS
    ]
    for job_id in stale:
        _jobs.pop(job_id, None)


def _append_log(job: dict, event_type: str, line: str) -> None:
    logs = job.setdefault("logs", [])
    logs.append({"type": event_type, "line": line, "ts": time.time()})
    if len(logs) > _MAX_LOG_LINES:
        del logs[: len(logs) - _MAX_LOG_LINES]
    # Mirror into backend logs so the app terminal shows activity.
    if event_type == "error":
        logger.error("[benchmark] %s", line)
    else:
        logger.info("[benchmark] %s", line)


def _resolve_run_id(started_at: float) -> Optional[str]:
    results_dir = _results_dir()
    new_files = [
        f for f in results_dir.glob("benchmark_*.json")
        if f.stat().st_mtime > started_at - 1.0
    ]
    if not new_files:
        return None
    newest = max(new_files, key=lambda f: f.stat().st_mtime)
    return newest.stem


def _finalize_job(job: dict, exit_code: Optional[int]) -> None:
    if job.get("status") in ("done", "failed"):
        return
    if exit_code == 0:
        run_id = _resolve_run_id(job.get("started_at", time.time()))
        job["status"] = "done"
        job["run_id"] = run_id
        job["error"] = None
        _append_log(job, "done", f"Benchmark complete. Run ID: {run_id}")
    else:
        job["status"] = "failed"
        job["error"] = f"Benchmark process exited with code {exit_code}"
        _append_log(job, "error", job["error"])


async def _drain_job_output(job_id: str) -> None:
    """Read subprocess stdout continuously, independent of SSE consumers.

    This prevents silent UI when Next.js rewrites buffer SSE, and ensures
    status polling still has logs/progress after the process finishes.
    """
    job = _jobs.get(job_id)
    if not job:
        return
    proc: asyncio.subprocess.Process = job["proc"]
    try:
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                continue
            if line.startswith("##PROGRESS##"):
                _append_log(job, "progress", line)
                m = re.search(r"##PROGRESS##\s+(\d+)/(\d+)(?:\s+(\S+))?", line)
                if m:
                    job["progress"] = {
                        "done": int(m.group(1)),
                        "total": int(m.group(2)),
                        "model_id": m.group(3),
                    }
            else:
                _append_log(job, "log", line)

        await proc.wait()
        _finalize_job(job, proc.returncode)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Benchmark reader failed for job %s", job_id)
        job["status"] = "failed"
        job["error"] = str(exc)
        _append_log(job, "error", f"Reader error: {exc}")


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Model-listing helpers (mirrors filter logic in scripts/benchmark_models.py)
# ---------------------------------------------------------------------------

def _is_e2ee_or_tee(model: dict) -> bool:
    caps = (model.get("model_spec") or {}).get("capabilities") or {}
    return (
        caps.get("supportsE2EE") is True
        or caps.get("supportsTeeAttestation") is True
        or (model.get("id") or "").startswith("e2ee-")
    )


async def _fetch_and_filter_text_models(api_key: str) -> list[dict]:
    client = VeniceAPIClient(api_key)
    data = await client.get_json("/models", params={"type": "text"})
    raw = data.get("data", [])
    result = []
    for m in raw:
        spec = m.get("model_spec") or {}
        privacy = (spec.get("privacy") or "").lower()
        if privacy not in ("private", "anonymized"):
            continue
        if _is_e2ee_or_tee(m):
            continue
        result.append(m)
    return result


def _model_to_summary(m: dict) -> dict:
    spec = m.get("model_spec") or {}
    caps = spec.get("capabilities") or {}
    pricing = spec.get("pricing") or {}
    return {
        "id": m.get("id", ""),
        "display_name": m.get("id", ""),
        "privacy": (spec.get("privacy") or "unknown").lower(),
        "capabilities": {
            "supportsFunctionCalling": caps.get("supportsFunctionCalling", False),
            "supportsReasoning": caps.get("supportsReasoning", False),
            "supportsReasoningEffort": caps.get("supportsReasoningEffort", False),
            "supportsResponseSchema": caps.get("supportsResponseSchema", False),
            "supportsVision": caps.get("supportsVision", False),
        },
        "pricing_input_usd": (pricing.get("input") or {}).get("usd"),
        "pricing_output_usd": (pricing.get("output") or {}).get("usd"),
        "deprecation": spec.get("deprecation"),
    }


def _filter_by_privacy(raw: list[dict], privacy: str) -> list[dict]:
    allowed = {"private", "anonymized"} if privacy == "both" else {privacy}
    result = []
    for m in raw:
        p = ((m.get("model_spec") or {}).get("privacy") or "").lower()
        if p in allowed:
            result.append(m)
    return result


def _estimate_cost(
    models: list[dict],
    tests: list[str],
    iterations: int,
    results_dir: Path,
) -> tuple[int, float, int, list[str]]:
    """Return (estimated_calls, estimated_usd, skipped_test_slots, warnings)."""
    historical = _load_historical_completion_estimates(results_dir)
    total_calls = 0
    total_usd = 0.0
    skipped = 0
    warnings: list[str] = []

    for m in models:
        summary = _model_to_summary(m)
        model_id = summary["id"]
        caps = summary["capabilities"]
        pin = summary["pricing_input_usd"] or 0.0
        pout = summary["pricing_output_usd"] or 0.0

        for tid in tests:
            if tid == "T2" and not caps.get("supportsFunctionCalling"):
                skipped += 1
                continue
            calls_per_iter = 3 if tid == "T6" else 1
            calls = calls_per_iter * iterations
            total_calls += calls

            prompt_tok, fallback_completion_tok = _TOKEN_ESTIMATES.get(tid, (50, 50))
            completion_tok = int(historical.get(model_id, {}).get(tid, fallback_completion_tok))
            total_usd += (
                (prompt_tok * calls * pin / 1_000_000)
                + (completion_tok * calls * pout / 1_000_000)
            )

            if model_id in _ALWAYS_REASONING_MODELS and tid not in historical.get(model_id, {}):
                warnings.append(
                    f"{model_id} always reasons; {tid} estimate uses a ceiling and may be low."
                )

    return total_calls, total_usd, skipped, warnings


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/benchmark/runs")
async def list_runs():
    """List all benchmark result files, newest first."""
    results_dir = _results_dir()
    files = sorted(
        results_dir.glob("benchmark_*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    runs = []
    for f in files:
        try:
            with f.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            logger.warning("Could not parse %s: %s", f.name, exc)
            continue

        generated_at = data.get("generated_at", "")
        model_count = data.get("model_count", 0)

        try:
            dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            timestamp = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            timestamp = generated_at

        runs.append({
            "run_id": f.stem,
            "filename": f.name,
            "generated_at": generated_at,
            "model_count": model_count,
            "timestamp": timestamp,
        })

    return {"runs": runs}


@router.get("/benchmark/runs/{run_id}")
async def get_run(run_id: str):
    """Return full results for a specific benchmark run."""
    # Sanitize run_id to prevent path traversal
    safe_id = Path(run_id).name
    target = _results_dir() / f"{safe_id}.json"
    if not target.exists():
        raise HTTPException(404, f"Run '{run_id}' not found")
    try:
        with target.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Inject run_id (the filename stem) so the frontend can reference it
        data["run_id"] = safe_id
        return data
    except Exception as exc:
        raise HTTPException(500, f"Failed to load run: {exc}") from exc


@router.get("/benchmark/models")
async def list_benchmark_models():
    """Return qualifying Venice text models with capabilities and pricing."""
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    if not api_key:
        raise HTTPException(400, "No Venice API key configured in settings")

    try:
        raw = await _fetch_and_filter_text_models(api_key)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice API error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Failed to fetch models: {exc}") from exc

    models = [_model_to_summary(m) for m in sorted(raw, key=lambda x: x.get("id", ""))]
    return {"models": models, "count": len(models)}


@router.post("/benchmark/estimate")
async def estimate_benchmark(request: Request):
    """Dry-run cost estimate for a planned benchmark (no job started)."""
    try:
        raw_body = await request.json()
        params = BenchmarkEstimateParams.model_validate(
            raw_body if isinstance(raw_body, dict) else {}
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON body: {exc}") from exc

    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    if not api_key:
        raise HTTPException(400, "No Venice API key configured in settings")

    privacy = (params.privacy or "both").lower()
    if privacy not in ("both", "private", "anonymized"):
        raise HTTPException(422, "privacy must be both|private|anonymized")

    tests = params.tests or list(_ALL_TESTS)
    tests = [t.strip().upper() for t in tests if t and str(t).strip()]
    unknown = [t for t in tests if t not in _ALL_TESTS]
    if unknown:
        raise HTTPException(422, f"Unknown tests: {unknown}")
    if not tests:
        raise HTTPException(422, "At least one test is required")

    try:
        raw = await _fetch_and_filter_text_models(api_key)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice API error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Failed to fetch models: {exc}") from exc

    raw = _filter_by_privacy(raw, privacy)
    by_id = {m.get("id"): m for m in raw if m.get("id")}

    if params.models:
        selected = []
        missing = []
        for mid in params.models:
            if mid in by_id:
                selected.append(by_id[mid])
            else:
                missing.append(mid)
        if not selected:
            raise HTTPException(
                400,
                f"None of the requested models are qualifying (missing/filtered: {missing})",
            )
        models = selected
    else:
        models = list(by_id.values())

    if not models:
        raise HTTPException(400, "No models match the selected privacy filter")

    models = sorted(models, key=lambda m: m.get("id", ""))
    calls, usd, skipped, warnings = _estimate_cost(models, tests, params.iterations, _results_dir())
    model_ids = [m.get("id", "") for m in models]

    note_skip = None
    if skipped:
        note_skip = (
            f"{skipped} model/test combination(s) would be skipped "
            f"(e.g. T2 without function calling)."
        )

    note = "Estimate uses historical averages where available; actual cost may vary."
    if warnings:
        note += " " + " ".join(warnings)

    return BenchmarkEstimateResponse(
        model_count=len(models),
        model_ids=model_ids,
        tests=tests,
        iterations=params.iterations,
        workers=params.workers,
        privacy=privacy,
        estimated_calls=calls,
        estimated_usd=round(usd, 6),
        skipped_tests_note=note_skip,
        note=note,
    ).model_dump()


@router.post("/benchmark/start")
@limiter.limit("10/hour")
async def start_benchmark(request: Request):
    """Start a benchmark subprocess. Returns a job_id for streaming/status.

    Body is parsed manually so SlowAPI's decorator does not break FastAPI body
    inference (which otherwise yields 422 query.params required).
    """
    try:
        raw = await request.json()
        params = BenchmarkStartParams.model_validate(raw if isinstance(raw, dict) else {})
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON body: {exc}") from exc

    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    admin_key = settings.VENICE_ADMIN_KEY or settings.VENICE_API_KEY
    if not api_key:
        raise HTTPException(400, "No Venice API key configured in settings")

    _cleanup_stale_jobs()

    running = sum(1 for j in _jobs.values() if j.get("status") == "running")
    if running >= _MAX_CONCURRENT_JOBS:
        raise HTTPException(
            429,
            f"Only {_MAX_CONCURRENT_JOBS} concurrent benchmark job(s) allowed. Please wait for the current run to finish."
        )

    if not _BENCHMARK_SCRIPT.exists():
        raise HTTPException(
            503,
            "Benchmark runner is not available in this deployment"
        )

    results_abs = str(_results_dir().resolve())

    cmd: list[str] = [
        sys.executable,
        str(_BENCHMARK_SCRIPT),
        "--api-key", api_key,
        "--admin-key", admin_key,
        "--iterations", str(params.iterations),
        "--workers", str(params.workers),
        "--privacy", params.privacy,
        "--output", results_abs,
        "--yes",
        "--no-infographic",
    ]

    if params.tests:
        cmd.extend(["--tests", ",".join(params.tests)])
    if params.models:
        cmd.extend(["--models", ",".join(params.models)])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_REPO_ROOT),
        )
    except Exception as exc:
        raise HTTPException(500, f"Failed to start benchmark: {exc}") from exc

    job_id = str(uuid.uuid4())
    job = {
        "proc": proc,
        "status": "running",
        "run_id": None,
        "started_at": time.time(),
        "logs": [],
        "progress": None,
        "error": None,
        "reader_task": None,
    }
    _jobs[job_id] = job
    _append_log(job, "log", f"Started benchmark subprocess pid={proc.pid}")
    job["reader_task"] = asyncio.create_task(_drain_job_output(job_id))
    logger.info("Benchmark job %s started (pid %s)", job_id, proc.pid)
    return {"job_id": job_id}


@router.get("/benchmark/stream/{job_id}")
async def stream_benchmark(job_id: str):
    """SSE stream of benchmark logs/progress.

    Reads from the in-memory job log buffer (filled by a background reader),
    so progress still works even if the browser reconnects or SSE is buffered.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        cursor = 0
        # Immediate hello so the UI is not blank while waiting for first model.
        yield {
            "data": json.dumps({
                "type": "log",
                "line": f"Streaming job {job_id} (status={job.get('status')})",
            })
        }

        try:
            while True:
                logs = job.get("logs") or []
                while cursor < len(logs):
                    entry = logs[cursor]
                    cursor += 1
                    yield {
                        "data": json.dumps({
                            "type": entry.get("type", "log"),
                            "line": entry.get("line", ""),
                            "run_id": job.get("run_id"),
                            "exit_code": None,
                        })
                    }

                status = job.get("status")
                if status in ("done", "failed") and cursor >= len(logs):
                    if status == "done":
                        yield {
                            "data": json.dumps({
                                "type": "done",
                                "run_id": job.get("run_id"),
                            })
                        }
                    else:
                        yield {
                            "data": json.dumps({
                                "type": "error",
                                "exit_code": 1,
                                "message": job.get("error") or "Benchmark failed",
                            })
                        }
                    break

                await asyncio.sleep(0.4)
        except Exception as exc:
            logger.error("SSE stream error for job %s: %s", job_id, exc)
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}

    return EventSourceResponse(event_generator())


@router.get("/benchmark/status/{job_id}")
async def job_status(job_id: str):
    """Return current status of a benchmark job (poll-friendly)."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Eagerly finalize if process ended but reader hasn't updated yet.
    proc: asyncio.subprocess.Process = job["proc"]
    if job["status"] == "running" and proc.returncode is not None:
        _finalize_job(job, proc.returncode)

    logs = job.get("logs") or []
    # Return a tail so the UI can catch up without SSE.
    tail = logs[-80:] if logs else []

    return {
        "status": job["status"],
        "run_id": job.get("run_id"),
        "error": job.get("error"),
        "progress": job.get("progress"),
        "log_count": len(logs),
        "logs": tail,
    }


# ---------------------------------------------------------------------------
# Infographic generation
# ---------------------------------------------------------------------------

_TEST_SHORT = {
    "T1": "Latency",
    "T2": "Tool Calling",
    "T3": "Structured Output",
    "T4": "Instruction Following",
    "T5": "Reasoning Quality",
    "T6": "Context Coherence",
    "T7": "Consistency",
    "T8": "Conciseness",
}


def _build_infographic_prompt(models: list[dict]) -> str:
    sorted_models = sorted(
        models,
        key=lambda r: r.get("composite_score") or -1,
        reverse=True,
    )
    top5 = [m for m in sorted_models[:5] if m.get("composite_score") is not None]
    top_lines = "\n".join(
        f"{i + 1}. {m['model_id']} — {m['composite_score']:.1f}/100"
        for i, m in enumerate(top5)
    )

    # Find weakest category
    category_scores: dict[str, list[float]] = {}
    for m in sorted_models:
        for tid, cat in m.get("categories", {}).items():
            if not cat.get("skipped") and cat.get("score_mean") is not None:
                category_scores.setdefault(tid, []).append(cat["score_mean"])

    worst_tid = None
    worst_avg = 999.0
    for tid, scores in category_scores.items():
        avg = sum(scores) / len(scores)
        if avg < worst_avg:
            worst_avg = avg
            worst_tid = tid

    weakest_note = (
        f"The weakest category was {_TEST_SHORT.get(worst_tid or '', worst_tid or '')} "
        f"with an average score of {worst_avg * 100:.0f}%."
        if worst_tid else ""
    )

    return (
        f"A professional dark-mode 4K benchmark infographic titled 'Venice AI Text Model Benchmark'. "
        f"Shows results for {len(models)} AI language models across 8 performance categories: "
        f"Latency, Tool Calling, Structured Output, Instruction Following, Reasoning Quality, "
        f"Context Coherence, Consistency, and Conciseness. "
        f"Top 5 models by composite score:\n{top_lines}\n"
        f"{weakest_note} "
        f"Color scheme: dark navy background, indigo accent bars, green for high scores, "
        f"amber for mid, red for low. Modern, clean, data-focused design. No photo-realistic elements."
    )


async def _resolve_image_model(api_key: str) -> str:
    """Discover a current image model via /models/traits; fall back to flux-2-pro."""
    client = VeniceAPIClient(api_key)
    try:
        traits = await client.get_json("/models/traits")
        # Traits payload may be {data: {...}} or a flat mapping.
        mapping = traits.get("data", traits) if isinstance(traits, dict) else {}
        for key in ("image:fast", "image:default", "image"):
            model_id = mapping.get(key)
            if isinstance(model_id, str) and model_id:
                return model_id
            if isinstance(model_id, dict):
                mid = model_id.get("id") or model_id.get("model")
                if mid:
                    return mid
    except Exception as exc:
        logger.warning("Could not resolve image model from traits: %s", exc)
    return "flux-2-pro"


async def _call_venice_image(api_key: str, prompt: str) -> str:
    """Async Venice image call using discovered model trait when available."""
    model_id = await _resolve_image_model(api_key)
    client = VeniceAPIClient(api_key)
    payload = {
        "model": model_id,
        "prompt": prompt,
        "resolution": "4K",
        "aspect_ratio": "16:9",
        "format": "png",
        "safe_mode": True,
        "return_binary": False,
    }
    data = await client.post_json("/image/generate", data=payload, timeout=120.0)
    images = data.get("images", [])
    if not images:
        raise ValueError("Venice image API returned no images")
    return images[0]  # base64 string


@router.post("/benchmark/infographic/{run_id}")
async def generate_infographic(run_id: str):
    """Generate a 4K PNG infographic for a benchmark run using Venice image API."""
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    if not api_key:
        raise HTTPException(400, "No Venice API key configured")

    safe_id = Path(run_id).name
    target = _results_dir() / f"{safe_id}.json"
    if not target.exists():
        raise HTTPException(404, f"Run '{run_id}' not found")

    try:
        with target.open("r", encoding="utf-8") as fh:
            run_data = json.load(fh)
    except Exception as exc:
        raise HTTPException(500, f"Failed to load run data: {exc}") from exc

    models = run_data.get("models", [])
    if not models:
        raise HTTPException(400, "Run contains no model data")

    prompt = _build_infographic_prompt(models)

    try:
        image_b64 = await _call_venice_image(api_key, prompt)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(502, f"Venice image API error: {detail}") from exc
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Infographic generation failed: {exc}") from exc

    return {"image_b64": image_b64, "prompt": prompt}

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
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

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
# {job_id: {"proc": asyncio.subprocess.Process, "status": str,
#            "run_id": str | None, "started_at": float}}

_MAX_CONCURRENT_JOBS = 1
_JOB_TTL_SECONDS = 3600


async def terminate_all_jobs():
    """Terminate all running benchmark jobs. Called during application shutdown."""
    for job_id, job in list(_jobs.items()):
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


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class BenchmarkStartParams(BaseModel):
    models: Optional[list[str]] = None   # None = all qualifying
    tests: Optional[list[str]] = None    # None = all 8 tests
    iterations: int = 10
    workers: int = 4
    privacy: str = "both"               # "both" | "private" | "anonymized"


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


def _fetch_and_filter_text_models(api_key: str) -> list[dict]:
    resp = requests.get(
        f"{_VENICE_BASE}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"type": "text"},
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json().get("data", [])
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
        raw = await asyncio.to_thread(_fetch_and_filter_text_models, api_key)
    except requests.HTTPError as exc:
        raise HTTPException(502, f"Venice API error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Failed to fetch models: {exc}") from exc

    models = [_model_to_summary(m) for m in sorted(raw, key=lambda x: x.get("id", ""))]
    return {"models": models, "count": len(models)}


@router.post("/benchmark/start")
async def start_benchmark(request: Request, params: BenchmarkStartParams):
    """Start a benchmark subprocess. Returns a job_id for streaming/status."""
    limiter = request.app.state.limiter
    await limiter.shared_limit("1/hour", scope="benchmark_start")(request)

    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
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
    _jobs[job_id] = {
        "proc": proc,
        "status": "running",
        "run_id": None,
        "started_at": time.time(),
    }
    logger.info("Benchmark job %s started (pid %s)", job_id, proc.pid)
    return {"job_id": job_id}


@router.get("/benchmark/stream/{job_id}")
async def stream_benchmark(job_id: str):
    """SSE stream of benchmark subprocess stdout. Emits log lines + final done/error event."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        proc: asyncio.subprocess.Process = job["proc"]
        started_at: float = job["started_at"]

        try:
            async for raw_line in proc.stdout:  # type: ignore[union-attr]
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                # Parse progress markers emitted by benchmark_models.py
                if line.startswith("##PROGRESS##"):
                    yield {"data": json.dumps({"type": "progress", "line": line})}
                else:
                    yield {"data": json.dumps({"type": "log", "line": line})}

            await proc.wait()
            exit_code = proc.returncode

            if exit_code == 0:
                # Find the newest JSON result file written after this job started
                results_dir = _results_dir()
                new_files = [
                    f for f in results_dir.glob("benchmark_*.json")
                    if f.stat().st_mtime > started_at
                ]
                run_id: Optional[str] = None
                if new_files:
                    newest = max(new_files, key=lambda f: f.stat().st_mtime)
                    run_id = newest.stem
                job["status"] = "done"
                job["run_id"] = run_id
                yield {"data": json.dumps({"type": "done", "run_id": run_id})}
            else:
                job["status"] = "failed"
                yield {"data": json.dumps({"type": "error", "exit_code": exit_code})}

        except Exception as exc:
            logger.error("SSE stream error for job %s: %s", job_id, exc)
            job["status"] = "failed"
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}

    return EventSourceResponse(event_generator())


@router.get("/benchmark/status/{job_id}")
async def job_status(job_id: str):
    """Return current status of a benchmark job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Eagerly update status if the process has finished but SSE wasn't consumed
    proc: asyncio.subprocess.Process = job["proc"]
    if job["status"] == "running" and proc.returncode is not None:
        if proc.returncode == 0:
            results_dir = _results_dir()
            new_files = [
                f for f in results_dir.glob("benchmark_*.json")
                if f.stat().st_mtime > job["started_at"]
            ]
            run_id: Optional[str] = None
            if new_files:
                newest = max(new_files, key=lambda f: f.stat().st_mtime)
                run_id = newest.stem
            job["status"] = "done"
            job["run_id"] = run_id
        else:
            job["status"] = "failed"

    return {
        "status": job["status"],
        "run_id": job.get("run_id"),
        "error": None if job["status"] != "failed" else "Benchmark process exited with non-zero status",
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


def _call_venice_image(api_key: str, prompt: str) -> str:
    """Synchronous Venice image call — run via asyncio.to_thread."""
    payload = {
        "model": "flux-2-pro",  # stable, generally available image model
        "prompt": prompt,
        "resolution": "4K",
        "aspect_ratio": "16:9",
        "format": "png",
        "safe_mode": True,
        "return_binary": False,
    }
    resp = requests.post(
        f"{_VENICE_BASE}/image/generate",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
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
        image_b64 = await asyncio.to_thread(_call_venice_image, api_key, prompt)
    except requests.HTTPError as exc:
        raise HTTPException(502, f"Venice image API error: {exc.response.text if exc.response else str(exc)}") from exc
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Infographic generation failed: {exc}") from exc

    return {"image_b64": image_b64, "prompt": prompt}

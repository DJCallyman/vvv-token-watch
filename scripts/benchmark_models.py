#!/usr/bin/env python3
"""
benchmark_models.py — Venice text model benchmark entry point.

Usage:
    python scripts/benchmark_models.py [options]

    --api-key KEY           Venice API key (default: $VENICE_API_KEY)
    --iterations N          Runs per test per model (default: 10)
    --workers N             Parallel model workers (default: 4)
    --tests T1,T2,...       Comma-separated test IDs (default: all)
    --model MODEL_ID        Benchmark a single model only
    --privacy both|private|anonymized  Filter privacy mode (default: both)
    --dry-run               Print qualifying models and test plan, then exit
    --output DIR            Results directory (default: scripts/results/)
    --yes                   Skip interactive confirmation
    --no-infographic        Skip 4K infographic generation
    --timeout SECS          Per-request timeout in seconds (default: 120)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# Load .env from the repo root (parent of scripts/) before anything reads env vars.
# Uses python-dotenv if available; silently skips if not installed.
try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env", override=False)
except ImportError:
    pass

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Make this runnable both as `python scripts/benchmark_models.py` and from
# the repo root with `python -m scripts.benchmark_models`
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_suite import ALL_TESTS
import benchmark_report as report

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

BASE_URL = "https://api.venice.ai/api/v1"
MAX_RETRIES = 3
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class BenchmarkClient:
    """Thin Venice API client with retry logic for benchmark scripts."""

    def __init__(self, api_key: str, timeout: int = 120):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "vvv-token-watch-benchmark/1.0",
        })

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        reraise=True,
    )
    def get(self, path: str, params: dict | None = None) -> dict:
        url = BASE_URL + path
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if resp.status_code in _RETRY_STATUSES:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    def post_json(self, path: str, payload: dict) -> dict:
        return self._post_with_retry(path, payload)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        reraise=True,
    )
    def _post_with_retry(self, path: str, payload: dict) -> dict:
        url = BASE_URL + path
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        if resp.status_code in _RETRY_STATUSES:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    @contextlib.contextmanager
    def post_stream(self, path: str, payload: dict) -> Iterator[requests.Response]:
        url = BASE_URL + path
        with self.session.post(url, json=payload, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            yield resp


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------

def fetch_text_models(client: BenchmarkClient) -> list[dict]:
    """Return all text models from the Venice API."""
    data = client.get("/models", params={"type": "text"})
    return data.get("data", [])


def is_e2ee_or_tee(model: dict) -> bool:
    """Return True if the model should be excluded (E2EE or TEE)."""
    model_id = model.get("id", "")
    if model_id.startswith("e2ee-"):
        return True
    caps = (model.get("model_spec") or {}).get("capabilities") or {}
    if caps.get("supportsE2EE"):
        return True
    if caps.get("supportsTeeAttestation"):
        return True
    return False


def filter_models(models: list[dict], privacy_filter: str) -> list[dict]:
    """
    Filter to Private/Anonymized text models, excluding E2EE/TEE.

    privacy_filter: "both" | "private" | "anonymized"
    """
    result = []
    for m in models:
        spec = m.get("model_spec") or {}
        privacy = (spec.get("privacy") or "").lower()

        # Must be private or anonymized
        if privacy not in ("private", "anonymized"):
            continue

        # Exclude E2EE / TEE models
        if is_e2ee_or_tee(m):
            continue

        # Apply privacy sub-filter
        if privacy_filter == "private" and privacy != "private":
            continue
        if privacy_filter == "anonymized" and privacy != "anonymized":
            continue

        result.append(m)

    return result


def model_meta(model: dict) -> dict:
    """Extract a clean summary dict from a raw model object."""
    spec = model.get("model_spec") or {}
    caps = spec.get("capabilities") or {}
    pricing = spec.get("pricing") or {}
    return {
        "id": model["id"],
        "privacy": (spec.get("privacy") or "").lower(),
        "context_length": spec.get("availableContextTokens") or model.get("context_length") or 0,
        "max_completion_tokens": spec.get("maxCompletionTokens"),
        "capabilities": {
            "supportsFunctionCalling": caps.get("supportsFunctionCalling", False),
            "supportsReasoning": caps.get("supportsReasoning", False),
            "supportsReasoningEffort": caps.get("supportsReasoningEffort", False),
            "supportsResponseSchema": caps.get("supportsResponseSchema", False),
            "supportsVision": caps.get("supportsVision", False),
        },
        "pricing_input_usd": (pricing.get("input") or {}).get("usd"),
        "pricing_output_usd": (pricing.get("output") or {}).get("usd"),
        "description": spec.get("description", ""),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_model_test(
    client: BenchmarkClient,
    model: dict,
    test_ids: list[str],
    iterations: int,
) -> dict:
    """Run all requested tests for a single model. Returns aggregated result dict."""
    meta = model_meta(model)
    caps = meta["capabilities"]
    test_results: dict[str, list[dict]] = {}

    for tid in test_ids:
        _, test_fn = ALL_TESTS[tid]
        try:
            runs = test_fn(client, meta["id"], caps, iterations)
        except Exception as e:
            logger.error("Test %s failed for model %s: %s", tid, meta["id"], e)
            from benchmark_suite import _empty_result
            runs = [_empty_result(status="error", error=str(e))] * iterations
        test_results[tid] = runs

    return report.aggregate_model_results(meta["id"], meta, test_results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Venice text models across 8 quality dimensions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--api-key", default=os.environ.get("VENICE_API_KEY", ""),
                        help="Venice API key (default: $VENICE_API_KEY)")
    parser.add_argument("--iterations", type=int, default=10,
                        help="Iterations per test per model (default: 10)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel model workers (default: 4)")
    parser.add_argument("--tests", default="",
                        help="Comma-separated test IDs e.g. T1,T2,T4 (default: all)")
    parser.add_argument("--model", default="",
                        help="Benchmark a single model ID only")
    parser.add_argument("--privacy", choices=["both", "private", "anonymized"], default="both",
                        help="Privacy mode filter (default: both)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List qualifying models and exit")
    parser.add_argument("--output", default=str(_SCRIPTS_DIR / "results"),
                        help="Results directory (default: scripts/results/)")
    parser.add_argument("--yes", action="store_true",
                        help="Skip interactive confirmation")
    parser.add_argument("--no-infographic", action="store_true",
                        help="Skip 4K infographic generation")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-request timeout in seconds (default: 120)")
    return parser.parse_args()


def _confirm(message: str) -> bool:
    try:
        answer = input(f"{message} [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _estimate_calls(model_count: int, test_ids: list[str], iterations: int) -> int:
    return model_count * len(test_ids) * iterations


def main() -> int:
    args = parse_args()

    # --- Validate API key ---
    if not args.api_key:
        print("Error: Venice API key required. Set $VENICE_API_KEY or use --api-key.", file=sys.stderr)
        return 1

    client = BenchmarkClient(api_key=args.api_key, timeout=args.timeout)

    # --- Resolve test IDs ---
    if args.tests:
        requested = [t.strip().upper() for t in args.tests.split(",")]
        invalid = [t for t in requested if t not in ALL_TESTS]
        if invalid:
            print(f"Error: Unknown test IDs: {', '.join(invalid)}. Valid: {', '.join(ALL_TESTS)}", file=sys.stderr)
            return 1
        test_ids = requested
    else:
        test_ids = list(ALL_TESTS.keys())

    # --- Fetch models ---
    print("Fetching text models from Venice API...")
    try:
        raw_models = fetch_text_models(client)
    except Exception as e:
        print(f"Error fetching models: {e}", file=sys.stderr)
        return 1

    # --- Filter models ---
    filtered = filter_models(raw_models, args.privacy)

    if args.model:
        filtered = [m for m in filtered if m.get("id") == args.model]
        if not filtered:
            print(f"Error: Model '{args.model}' not found or excluded by privacy filter.", file=sys.stderr)
            return 1

    if not filtered:
        print("No qualifying models found.", file=sys.stderr)
        return 1

    # --- Print model list ---
    print(f"\nQualifying models ({len(filtered)} total):\n")
    header = f"  {'Model ID':<45} {'Privacy':<12} {'Context':<10} {'Tools':<6} {'Reasoning'}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for m in sorted(filtered, key=lambda x: x.get("id", "")):
        spec = m.get("model_spec") or {}
        caps = (spec.get("capabilities") or {})
        privacy = (spec.get("privacy") or "?").capitalize()
        ctx_k = ((spec.get("availableContextTokens") or m.get("context_length") or 0) // 1000)
        tools = "Yes" if caps.get("supportsFunctionCalling") else "No"
        reasoning = "Yes" if caps.get("supportsReasoning") else "No"
        print(f"  {m['id']:<45} {privacy:<12} {ctx_k}K{'':<8} {tools:<6} {reasoning}")

    print(f"\nTests to run: {', '.join(test_ids)}")
    print(f"Iterations per test: {args.iterations}")
    print(f"Parallel workers: {args.workers}")
    approx_calls = _estimate_calls(len(filtered), test_ids, args.iterations)
    print(f"Estimated API calls: ~{approx_calls:,}")

    if args.dry_run:
        print("\n[dry-run] Exiting without running tests.")
        return 0

    # --- Confirmation ---
    if not args.yes:
        if not _confirm(f"\nProceed with benchmarking {len(filtered)} models?"):
            print("Aborted.")
            return 0

    # --- Run benchmarks ---
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    all_model_results: list[dict] = []
    tasks = [(m, test_ids, args.iterations) for m in filtered]

    print(f"\nRunning benchmarks with {args.workers} parallel workers...\n")
    start_time = time.time()

    with tqdm(total=len(tasks), desc="Models", unit="model") as pbar:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_model = {
                executor.submit(run_model_test, client, m, tids, iters): m["id"]
                for m, tids, iters in tasks
            }
            for future in as_completed(future_to_model):
                model_id = future_to_model[future]
                try:
                    result = future.result()
                    all_model_results.append(result)
                except Exception as e:
                    logger.error("Model %s benchmark failed: %s", model_id, e)
                    # Add a stub result so the model appears in the report
                    all_model_results.append({
                        "model_id": model_id,
                        "model_meta": {"id": model_id},
                        "categories": {},
                        "composite_score": None,
                    })
                finally:
                    pbar.update(1)
                    pbar.set_postfix_str(f"last: {model_id}")

    elapsed = time.time() - start_time
    print(f"\nBenchmark complete in {elapsed:.1f}s")

    # --- Normalize T1 + compute composite scores ---
    report.compute_composite_scores(all_model_results)

    # --- Reports ---
    # 1. JSON
    json_path = output_dir / f"benchmark_{timestamp}.json"
    report.write_json(all_model_results, json_path)
    print(f"\nJSON results: {json_path}")

    # 2. Terminal table
    report.print_terminal_table(all_model_results, test_ids)

    # 3. HTML
    html_path = output_dir / f"benchmark_{timestamp}.html"
    report.write_html(all_model_results, test_ids, args.iterations, html_path)
    print(f"HTML report: {html_path}")

    # 4. Infographic
    if not args.no_infographic:
        print("Generating 4K infographic...")
        png_path = report.generate_infographic(all_model_results, test_ids, output_dir)
        if png_path:
            print(f"Infographic: {png_path}")
        else:
            print("[report] Infographic skipped or failed (see warnings above)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

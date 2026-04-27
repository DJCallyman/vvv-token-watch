"""
benchmark_report.py — Output formatters for the Venice text model benchmark.

Four output formats:
  1. JSON  — full raw + aggregated results file
  2. Terminal — tabulate table with per-category scores + composite
  3. HTML  — sortable table + inline Chart.js bar charts per category
  4. Infographic — 4K PNG via Venice image-gen API
"""

from __future__ import annotations

import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tabulate import tabulate

# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float | None:
    cleaned = [v for v in values if v is not None]
    return round(statistics.mean(cleaned), 4) if cleaned else None


def _stdev(values: list[float]) -> float | None:
    cleaned = [v for v in values if v is not None]
    return round(statistics.stdev(cleaned), 4) if len(cleaned) >= 2 else None


def _percentile(values: list[float], pct: int) -> float | None:
    cleaned = sorted(v for v in values if v is not None)
    if not cleaned:
        return None
    idx = int(math.ceil(pct / 100.0 * len(cleaned))) - 1
    return round(cleaned[max(0, idx)], 4)


def aggregate_model_results(model_id: str, model_meta: dict, test_results: dict[str, list[dict]]) -> dict:
    """
    Given raw per-run results for each test, compute:
     - per-category aggregate stats
     - latency normalization deferred — done later at report level
     - composite score (mean of category scores, excluding T1 until normalized)
    """
    categories = {}
    for test_id, runs in test_results.items():
        success_runs = [r for r in runs if r["status"] == "success"]
        skip_runs = [r for r in runs if r["status"] == "skip"]
        error_runs = [r for r in runs if r["status"] in ("error", "timeout")]

        scores = [r["score"] for r in success_runs if r["score"] is not None]
        latencies = [r["latency_ms"] for r in success_runs if r["latency_ms"] is not None]
        ttfts = [r["ttft_ms"] for r in success_runs if r["ttft_ms"] is not None]
        tps_list = [r["tokens_per_sec"] for r in success_runs if r["tokens_per_sec"] is not None]
        tc_list = [r["tokens_completion"] for r in success_runs if r["tokens_completion"] is not None]
        tp_list = [r["tokens_prompt"] for r in success_runs if r["tokens_prompt"] is not None]

        categories[test_id] = {
            "runs_total": len(runs),
            "runs_success": len(success_runs),
            "runs_error": len(error_runs),
            "runs_skip": len(skip_runs),
            "skipped": len(skip_runs) == len(runs),
            # Scores
            "score_mean": _mean(scores),
            "score_stdev": _stdev(scores),
            # Latency
            "latency_mean_ms": _mean(latencies),
            "latency_median_ms": _percentile(latencies, 50),
            "latency_p90_ms": _percentile(latencies, 90),
            "latency_p95_ms": _percentile(latencies, 95),
            "latency_min_ms": round(min(latencies), 2) if latencies else None,
            "latency_max_ms": round(max(latencies), 2) if latencies else None,
            "latency_stdev_ms": _stdev(latencies),
            # TTFT (T1 only)
            "ttft_mean_ms": _mean(ttfts),
            "ttft_median_ms": _percentile(ttfts, 50),
            # Throughput
            "tokens_per_sec_mean": _mean(tps_list),
            "tokens_completion_mean": _mean(tc_list),
            "tokens_prompt_mean": _mean(tp_list),
            # Raw runs for debugging
            "runs": runs,
        }

    return {
        "model_id": model_id,
        "model_meta": model_meta,
        "categories": categories,
        # composite computed later after T1 latency normalization
        "composite_score": None,
    }


def compute_composite_scores(all_model_results: list[dict]) -> None:
    """
    Normalize T1 latency scores across all models, then compute composite scores.
    Called in-place after all models have been aggregated.
    T1 score = 1 - (latency_mean / max_latency_across_models)

    Composite scoring uses reliability-weighted effective scores:
    - For categories with partial errors: blend actual score with global category average,
      weighted by (runs_success / runs_total). This applies Bayesian shrinkage — errored
      runs are treated as "unknown, assume average" rather than zero.
    - For categories where ALL runs errored: substitute the global category average.
    - For skipped categories (model doesn't support the feature): excluded entirely.
    - Genuine failures (model completed runs but scored 0%) remain at 0%.

    This prevents models with sparse successful data (due to API errors) from appearing
    at the top of rankings, while not penalising genuine capability failures.
    """
    # --- Step 1: Normalize T1 latency scores ---
    t1_latencies = [
        r["categories"]["T1"]["latency_mean_ms"]
        for r in all_model_results
        if "T1" in r["categories"] and r["categories"]["T1"]["latency_mean_ms"] is not None
    ]
    max_latency = max(t1_latencies) if t1_latencies else None

    for model_result in all_model_results:
        cats = model_result["categories"]
        if "T1" in cats and max_latency:
            t1_lat = cats["T1"]["latency_mean_ms"]
            if t1_lat is not None and max_latency > 0:
                cats["T1"]["score_mean"] = round(1.0 - (t1_lat / max_latency), 4)
            else:
                cats["T1"]["score_mean"] = None

    # --- Step 2: Compute global average per test category (over models with actual data) ---
    all_test_ids: set[str] = set()
    for m in all_model_results:
        all_test_ids.update(m["categories"].keys())

    global_avgs: dict[str, float] = {}
    for tid in all_test_ids:
        valid_scores = [
            m["categories"][tid]["score_mean"]
            for m in all_model_results
            if tid in m["categories"]
            and not m["categories"][tid].get("skipped")
            and m["categories"][tid].get("score_mean") is not None
            and m["categories"][tid].get("runs_success", 0) > 0
        ]
        global_avgs[tid] = statistics.mean(valid_scores) if valid_scores else 0.5

    # --- Step 3: Reliability-weighted composite per model ---
    for model_result in all_model_results:
        cats = model_result["categories"]
        effective_scores: list[float] = []

        for tid in sorted(cats.keys()):
            cat = cats[tid]
            if cat.get("skipped"):
                continue

            runs_success = cat.get("runs_success", 0)
            runs_error = cat.get("runs_error", 0)
            runs_total = runs_success + runs_error
            if runs_total == 0:
                continue

            g_avg = global_avgs.get(tid, 0.5)

            if runs_success > 0 and cat.get("score_mean") is not None:
                # Blend actual score with global average, weighted by run reliability
                effective = (cat["score_mean"] * runs_success + g_avg * runs_error) / runs_total
            else:
                # All runs errored — no data, assume global average
                effective = g_avg

            effective = round(effective, 4)
            cat["score_effective"] = effective  # stored for transparency
            effective_scores.append(effective)

        if effective_scores:
            model_result["composite_score"] = round(
                sum(effective_scores) / len(effective_scores) * 100, 2
            )
            cats_with_data = sum(
                1 for cat in cats.values()
                if not cat.get("skipped") and cat.get("runs_success", 0) > 0
            )
            cats_applicable = sum(1 for cat in cats.values() if not cat.get("skipped"))
            model_result["data_coverage"] = round(
                cats_with_data / cats_applicable, 3
            ) if cats_applicable else None
        else:
            model_result["composite_score"] = None
            model_result["data_coverage"] = None


# ---------------------------------------------------------------------------
# Format 1: JSON
# ---------------------------------------------------------------------------

def write_json(all_model_results: list[dict], output_path: Path) -> Path:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_count": len(all_model_results),
        "models": all_model_results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str))
    return output_path


# ---------------------------------------------------------------------------
# Format 2: Terminal table
# ---------------------------------------------------------------------------

_TEST_SHORT = {
    "T1": "Latency",
    "T2": "Tools",
    "T3": "JSON Schema",
    "T4": "Instr Follow",
    "T5": "Reasoning",
    "T6": "Ctx Coherence",
    "T7": "Consistency",
    "T8": "Conciseness",
}


def _score_cell(val: float | None, skipped: bool) -> str:
    if skipped:
        return "  -  "
    if val is None:
        return "  ?  "
    pct = round(val * 100, 1)
    return f"{pct:5.1f}%"


def print_terminal_table(all_model_results: list[dict], test_ids: list[str]) -> None:
    sorted_results = sorted(
        all_model_results,
        key=lambda r: r["composite_score"] if r["composite_score"] is not None else -1,
        reverse=True,
    )

    headers = ["#", "Model ID", "Privacy", "Ctx (K)", "Composite"] + [
        _TEST_SHORT.get(tid, tid) for tid in test_ids
    ]

    rows = []
    for rank, model_result in enumerate(sorted_results, start=1):
        meta = model_result["model_meta"]
        privacy = meta.get("privacy", "?").capitalize()
        ctx_k = meta.get("context_length", 0) // 1000
        composite = (
            f"{model_result['composite_score']:.1f}" if model_result["composite_score"] is not None else "?"
        )

        row = [rank, model_result["model_id"], privacy, f"{ctx_k}K", composite]
        for tid in test_ids:
            cat = model_result["categories"].get(tid, {})
            skipped = cat.get("skipped", True)
            score = cat.get("score_mean")
            row.append(_score_cell(score, skipped))

        rows.append(row)

    print("\n" + tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    print()


# ---------------------------------------------------------------------------
# Format 3: HTML report
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Venice Text Model Benchmark — {{ generated_at }}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3e;
    --text: #e2e8f0;
    --muted: #8892a4;
    --accent: #6366f1;
    --success: #22c55e;
    --warn: #f59e0b;
    --danger: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; padding: 2rem; }
  h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; }
  .meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; }
  .section-title { font-size: 1.1rem; font-weight: 600; margin: 2rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th { background: var(--surface); padding: 0.6rem 0.75rem; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); cursor: pointer; user-select: none; white-space: nowrap; }
  th:hover { color: var(--accent); }
  td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface); }
  .score-high { color: var(--success); font-weight: 600; }
  .score-mid  { color: var(--warn); }
  .score-low  { color: var(--danger); }
  .score-skip { color: var(--muted); }
  .badge-private { background: #1e3a5f; color: #60a5fa; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem; }
  .badge-anonymized { background: #3a2a0f; color: #fbbf24; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem; }
  .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 1.5rem; margin-top: 1rem; }
  .chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
  .chart-card h3 { font-size: 0.9rem; font-weight: 600; margin-bottom: 0.75rem; color: var(--muted); }
</style>
</head>
<body>

<h1>Venice Text Model Benchmark</h1>
<p class="meta">Generated: {{ generated_at }} &mdash; {{ model_count }} models &mdash; {{ iterations }} iterations/test</p>

<p class="section-title">Results by Composite Score</p>
<table id="results-table">
  <thead>
    <tr>
      <th onclick="sortTable(0)">#</th>
      <th onclick="sortTable(1)">Model ID</th>
      <th onclick="sortTable(2)">Privacy</th>
      <th onclick="sortTable(3)">Context</th>
      <th onclick="sortTable(4)">Composite</th>
      {% for tid, tname in test_headers %}
      <th onclick="sortTable({{ loop.index + 4 }})">{{ tname }}</th>
      {% endfor %}
      <th onclick="sortTable({{ test_headers|length + 5 }})">Latency (ms)</th>
      <th onclick="sortTable({{ test_headers|length + 6 }})">Tok/s</th>
    </tr>
  </thead>
  <tbody>
    {% for r in sorted_results %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ r.model_id }}</td>
      <td>
        {% if r.model_meta.privacy == 'private' %}
          <span class="badge-private">Private</span>
        {% else %}
          <span class="badge-anonymized">Anonymized</span>
        {% endif %}
      </td>
      <td>{{ (r.model_meta.context_length or 0) // 1000 }}K</td>
      <td class="{{ score_class(r.composite_score / 100 if r.composite_score else None) }}">
        {{ "%.1f"|format(r.composite_score) if r.composite_score is not none else "?" }}
      </td>
      {% for tid, _ in test_headers %}
      {% set cat = r.categories.get(tid, {}) %}
      {% set skipped = cat.get('skipped', True) %}
      {% set score = cat.get('score_mean') %}
      <td class="{{ 'score-skip' if skipped else score_class(score) }}">
        {{ "-" if skipped else ("%.1f%%"|format(score * 100) if score is not none else "?") }}
      </td>
      {% endfor %}
      <td>{{ "%.0f"|format(r.categories.get('T1', {}).get('latency_mean_ms') or 0) if r.categories.get('T1', {}).get('latency_mean_ms') else "?" }}</td>
      <td>{{ "%.1f"|format(r.categories.get('T1', {}).get('tokens_per_sec_mean') or 0) if r.categories.get('T1', {}).get('tokens_per_sec_mean') else "?" }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<p class="section-title">Per-Category Scores</p>
<div class="charts-grid">
  {% for tid, tname in test_headers %}
  <div class="chart-card">
    <h3>{{ tid }}: {{ tname }}</h3>
    <canvas id="chart-{{ tid }}" height="220"></canvas>
  </div>
  {% endfor %}
</div>

<script>
// ---- Sorting ----
let sortDir = {};
function sortTable(col) {
  const tbl = document.getElementById('results-table');
  const tbody = tbl.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc = (sortDir[col] = !sortDir[col]);
  rows.sort((a, b) => {
    const va = a.cells[col].innerText.replace('%','').trim();
    const vb = b.cells[col].innerText.replace('%','').trim();
    const na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
    return asc ? va.localeCompare(vb) : vb.localeCompare(va);
  });
  rows.forEach(r => tbody.appendChild(r));
}

// ---- Charts ----
const modelLabels = {{ model_labels | tojson }};
const chartData = {{ chart_data | tojson }};
const COLORS = ['#6366f1','#22c55e','#f59e0b','#ef4444','#06b6d4','#a78bfa','#fb923c','#34d399',
  '#818cf8','#86efac','#fcd34d','#fca5a5','#67e8f9','#c4b5fd','#fdba74','#6ee7b7'];

Object.entries(chartData).forEach(([tid, scores]) => {
  const ctx = document.getElementById('chart-' + tid);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: modelLabels,
      datasets: [{
        data: scores,
        backgroundColor: modelLabels.map((_, i) => COLORS[i % COLORS.length] + 'cc'),
        borderColor: modelLabels.map((_, i) => COLORS[i % COLORS.length]),
        borderWidth: 1,
        borderRadius: 3,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          min: 0, max: 100,
          ticks: { color: '#8892a4', callback: v => v + '%' },
          grid: { color: '#2a2d3e' }
        },
        y: {
          ticks: { color: '#8892a4', font: { size: 10 } },
          grid: { display: false }
        }
      }
    }
  });
});
</script>
</body>
</html>
"""


def _jinja_score_class(score):
    if score is None:
        return "score-skip"
    if score >= 0.75:
        return "score-high"
    if score >= 0.4:
        return "score-mid"
    return "score-low"


def write_html(all_model_results: list[dict], test_ids: list[str], iterations: int, output_path: Path) -> Path:
    try:
        from jinja2 import Environment
    except ImportError:
        print("[report] jinja2 not installed — skipping HTML report", file=sys.stderr)
        return output_path

    sorted_results = sorted(
        all_model_results,
        key=lambda r: r["composite_score"] if r["composite_score"] is not None else -1,
        reverse=True,
    )

    test_headers = [
        (tid, _TEST_SHORT.get(tid, tid)) for tid in test_ids
    ]

    # Chart data: for each test, list of scores per model (in sorted order)
    model_labels = [r["model_id"] for r in sorted_results]
    chart_data: dict[str, list] = {}
    for tid in test_ids:
        values = []
        for r in sorted_results:
            cat = r["categories"].get(tid, {})
            skipped = cat.get("skipped", True)
            score = cat.get("score_mean")
            if skipped or score is None:
                values.append(None)
            else:
                values.append(round(score * 100, 1))
        chart_data[tid] = values

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    env = Environment()
    env.globals["score_class"] = _jinja_score_class
    # Add tojson filter
    env.filters["tojson"] = lambda v: json.dumps(v)

    template = env.from_string(_HTML_TEMPLATE)
    html = template.render(
        generated_at=generated_at,
        model_count=len(all_model_results),
        iterations=iterations,
        sorted_results=sorted_results,
        test_headers=test_headers,
        model_labels=model_labels,
        chart_data=chart_data,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Format 4: Infographic (via venice-image-gen skill)
# ---------------------------------------------------------------------------

_INFOGRAPHIC_SKILL = Path("/Users/djcal/.agents/skills/venice-image-gen/scripts/generate_image.py")


def generate_infographic(all_model_results: list[dict], test_ids: list[str], output_dir: Path) -> Path | None:
    """
    Build a descriptive prompt summarising benchmark results and call the
    venice-image-gen skill script to produce a 4K PNG infographic.
    """
    if not _INFOGRAPHIC_SKILL.exists():
        print("[report] venice-image-gen skill not found — skipping infographic", file=sys.stderr)
        return None

    api_key = os.environ.get("VENICE_API_KEY", "")
    if not api_key:
        print("[report] VENICE_API_KEY not set — skipping infographic", file=sys.stderr)
        return None

    sorted_results = sorted(
        all_model_results,
        key=lambda r: r["composite_score"] if r["composite_score"] is not None else -1,
        reverse=True,
    )

    top5 = sorted_results[:5]
    top_lines = "\n".join(
        f"{i+1}. {r['model_id']} — {r['composite_score']:.1f}/100"
        for i, r in enumerate(top5)
        if r["composite_score"] is not None
    )

    bottom5 = sorted_results[-5:]
    weakest_category = {}
    for r in sorted_results:
        for tid in test_ids:
            cat = r["categories"].get(tid, {})
            if not cat.get("skipped") and cat.get("score_mean") is not None:
                weakest_category.setdefault(tid, []).append(cat["score_mean"])
    worst_tid = None
    worst_score = 999
    for tid, scores in weakest_category.items():
        avg = sum(scores) / len(scores)
        if avg < worst_score:
            worst_score = avg
            worst_tid = tid

    prompt = (
        f"A professional dark-mode 4K benchmark infographic titled 'Venice AI Text Model Benchmark'. "
        f"Shows results for {len(all_model_results)} AI language models across 8 performance categories: "
        f"Latency, Tool Calling, Structured Output, Instruction Following, Reasoning Quality, "
        f"Context Coherence, Consistency, and Conciseness. "
        f"Top 5 models by composite score:\n{top_lines}\n"
        f"The weakest category across all models was {_TEST_SHORT.get(worst_tid, worst_tid)} "
        f"with an average score of {worst_score*100:.0f}%. "
        f"Color scheme: dark navy background, indigo accent bars, green for high scores, "
        f"amber for mid, red for low. Modern, clean, data-focused design. No photo-realistic elements."
    )

    out_file = output_dir / "benchmark_infographic"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(_INFOGRAPHIC_SKILL),
        prompt,
        "--resolution", "4K",
        "--aspect_ratio", "16:9",
        "--format", "png",
        "--output", str(out_file),
    ]

    try:
        result = subprocess.run(
            cmd,
            env={**os.environ, "VENICE_API_KEY": api_key},
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            # Skill saves as out_file.png
            png_path = Path(str(out_file) + ".png")
            if not png_path.exists():
                # Try without extension
                png_path = out_file
            return png_path if png_path.exists() else None
        else:
            print(f"[report] Infographic generation failed:\n{result.stderr}", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("[report] Infographic generation timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[report] Infographic error: {e}", file=sys.stderr)
        return None

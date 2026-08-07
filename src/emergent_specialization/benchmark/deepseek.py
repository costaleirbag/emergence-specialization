"""Opt-in direct DeepSeek concurrency benchmark.

Without ``--confirm-real`` this command only prints a plan and performs no
credential lookup or network activity.  Live output is explicitly watermarked
as infrastructure-only and is written outside ``data/runs``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from ..config import load_config
from ..costs import estimate_usage_cost, normalize_token_usage
from ..credentials import CredentialStore
from ..providers.deepseek_direct import DeepSeekDirectBackend


REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((percentile / 100) * (len(ordered) - 1)))))
    return ordered[index]


def _parse_levels(value: str) -> tuple[int, ...]:
    levels = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not levels or any(level < 1 for level in levels) or len(set(levels)) != len(levels):
        raise ValueError("concurrency levels must be unique positive integers")
    return levels


async def _run_level(
    backend: DeepSeekDirectBackend,
    *,
    level: int,
    jobs: int,
    max_cost_usd: float | None,
    max_physical_attempts: int,
    input_rate: float | None,
    cached_rate: float | None,
    output_rate: float | None,
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(level)
    attempts = 0
    total_cost = 0.0
    results: list[dict[str, Any]] = []
    lock = asyncio.Lock()

    async def one(job: int) -> None:
        nonlocal attempts, total_cost
        async with semaphore:
            async with lock:
                if max_cost_usd is not None and total_cost >= max_cost_usd:
                    results.append({"success": False, "error_category": "budget_exhausted", "latency_s": 0.0})
                    return
                if attempts >= max_physical_attempts:
                    results.append({"success": False, "error_category": "attempt_budget_exhausted", "latency_s": 0.0})
                    return
                attempts += 1
            started = time.perf_counter()
            response = await backend.complete(
                system_prompt="Return JSON only. Infrastructure benchmark; not a scientific task.",
                user_prompt=(
                    f'Benchmark namespace concurrency-{level} job-{job}. '
                    'Return exactly {"answer": 0, "confidence": 0.0}.'
                ),
                model="deepseek-v4-flash",
                model_parameters={"max_tokens": 64},
            )
            usage = normalize_token_usage(response.token_usage)
            cost = estimate_usage_cost(
                response.token_usage,
                input_per_million_tokens=input_rate,
                cached_input_per_million_tokens=cached_rate,
                output_per_million_tokens=output_rate,
            )
            async with lock:
                if cost is not None:
                    total_cost += cost
            results.append(
                {
                    "success": response.error is None,
                    "error_category": response.error_category,
                    "http_status": response.http_status,
                    "latency_s": response.latency_s or (time.perf_counter() - started),
                    "usage": usage,
                    "cost_usd": cost,
                }
            )

    wall_started = time.perf_counter()
    await asyncio.gather(*(one(job) for job in range(jobs)))
    wall = time.perf_counter() - wall_started
    latencies = [float(item["latency_s"]) for item in results if item.get("latency_s") is not None]
    usage_rows = [item["usage"] for item in results if item.get("usage")]
    input_tokens = sum(float(row.get("input_tokens", 0)) for row in usage_rows)
    cached_tokens = sum(float(row.get("cached_input_tokens", 0)) for row in usage_rows)
    output_tokens = sum(float(row.get("output_tokens", 0)) for row in usage_rows)
    categories = [item.get("error_category") for item in results]
    return {
        "concurrency": level,
        "jobs": jobs,
        "attempts": attempts,
        "successes": sum(bool(item.get("success")) for item in results),
        "failures": sum(not bool(item.get("success")) for item in results),
        "retry_count": 0,
        "rate_limit_429_count": sum(item.get("http_status") == 429 for item in results),
        "server_5xx_count": sum(isinstance(item.get("http_status"), int) and 500 <= item["http_status"] < 600 for item in results),
        "timeout_count": sum(item.get("error_category") == "transient_transport" for item in results),
        "error_categories": {str(category): categories.count(category) for category in set(categories) if category},
        "throughput_requests_per_s": (len(results) / wall) if wall else None,
        "wall_time_s": wall,
        "latency_s": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "p50": _percentile(latencies, 50),
            "p90": _percentile(latencies, 90),
            "p95": _percentile(latencies, 95),
            "p99": _percentile(latencies, 99),
        },
        "input_tokens": input_tokens if usage_rows else None,
        "cached_input_tokens": cached_tokens if usage_rows else None,
        "cache_hit_ratio": (cached_tokens / input_tokens) if input_tokens else None,
        "output_tokens": output_tokens if usage_rows else None,
        "observed_cost_usd": total_cost if usage_rows else None,
        "cost_per_successful_completion": (
            total_cost / sum(bool(item.get("success")) for item in results)
            if sum(bool(item.get("success")) for item in results) and usage_rows
            else None
        ),
    }


def _recommend(rows: list[dict[str, Any]]) -> tuple[int | None, str]:
    viable = [
        row for row in rows
        if row["failures"] == 0
        and row["rate_limit_429_count"] == 0
        and row["timeout_count"] == 0
    ]
    if not viable:
        return None, "no tested level had zero failures, zero 429s, and zero timeouts"
    selected = viable[0]
    for row in viable[1:]:
        previous = selected
        previous_p95 = previous["latency_s"].get("p95")
        current_p95 = row["latency_s"].get("p95")
        previous_throughput = previous.get("throughput_requests_per_s") or 0.0
        current_throughput = row.get("throughput_requests_per_s") or 0.0
        gain = current_throughput / previous_throughput if previous_throughput else float("inf")
        p95_ratio = current_p95 / previous_p95 if previous_p95 else 1.0
        # Stop at a visible latency knee: less than 10% more throughput while
        # p95 grows by at least 50% is not a conservative probe setting.
        if gain < 1.10 and p95_ratio >= 1.50:
            break
        selected = row
    return selected["concurrency"], "highest viable level before a throughput/latency knee"


def _write_markdown(report: dict[str, Any], output: Path) -> None:
    rows = report["levels"]
    lines = [
        "# DeepSeek concurrency benchmark",
        "",
        "> **INFRASTRUCTURE BENCHMARK — NOT SCIENTIFIC DATA**",
        "",
        f"Model: `{report['model']}`  ",
        f"Nominal jobs: {report['jobs_per_level']} × {len(rows)} = {report['nominal_jobs_total']}  ",
        f"Physical-attempt ceiling: {report['max_physical_attempts_total']}  ",
        f"Budget ceiling: USD {report['max_cost_usd_total']:.2f}",
        "",
        "| concurrency | success/jobs | attempts | retries | 429 | 5xx | req/s | p50 s | p95 s | cost USD |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        latency = row["latency_s"]
        lines.append(
            f"| {row['concurrency']} | {row['successes']}/{row['jobs']} | {row['attempts']} | "
            f"{row['retry_count']} | {row['rate_limit_429_count']} | {row['server_5xx_count']} | "
            f"{row['throughput_requests_per_s']:.3f} | {latency['p50']:.3f} | {latency['p95']:.3f} | "
            f"{row['observed_cost_usd'] if row['observed_cost_usd'] is not None else 'n/a'} |"
        )
    lines += [
        "",
        f"**Recommended probe concurrency:** `{report['recommended_probe_concurrency']}`",
        f"Reason: {report['recommendation_reason']}.",
        "",
        "Retry count is zero by design: this benchmark uses one physical attempt per job to measure raw provider/runtime behavior; scientific runs retain the explicit runtime retry policy.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run_live(config_path: str, levels: tuple[int, ...], jobs: int, max_cost_usd: float | None, max_physical_attempts: int, output: Path) -> dict[str, Any]:
    config_file = _resolve_path(config_path)
    config = load_config(config_file)
    if config.agent.backend != "deepseek_direct":
        raise ValueError("benchmark requires a deepseek_direct config")
    key = CredentialStore(config.runtime.credential_service, config.runtime.credential_account).get(
        source=config.runtime.credential_source
    )
    backend = DeepSeekDirectBackend(
        api_key=key,
        base_url=config.runtime.api_base_url,
        thinking=config.agent.thinking,
        max_tokens=64,
        connect_timeout_s=config.runtime.connect_timeout_s,
        read_timeout_s=config.runtime.read_timeout_s,
        request_timeout_s=config.runtime.request_timeout_s,
        pool_timeout_s=config.runtime.pool_timeout_s,
        user_id=config.runtime.user_id,
        credential_source=config.runtime.credential_source,
        max_connections=max(levels),
        max_keepalive_connections=max(levels),
    )
    try:
        rows = []
        remaining_budget = max_cost_usd
        remaining_attempts = max_physical_attempts
        for level in levels:
            row = await _run_level(
                    backend,
                    level=level,
                    jobs=jobs,
                    max_cost_usd=remaining_budget,
                    max_physical_attempts=remaining_attempts,
                    input_rate=config.cost.input_per_million_tokens,
                    cached_rate=config.cost.cached_input_per_million_tokens,
                    output_rate=config.cost.output_per_million_tokens,
                )
            rows.append(row)
            remaining_attempts = max(0, remaining_attempts - int(row["attempts"]))
            if remaining_budget is not None and row.get("observed_cost_usd") is not None:
                remaining_budget = max(0.0, remaining_budget - float(row["observed_cost_usd"]))
    finally:
        await backend.close()
    recommendation, recommendation_reason = _recommend(rows)
    baseline_throughput = next(
        (row.get("throughput_requests_per_s") for row in rows if row["concurrency"] == 4),
        None,
    )
    for row in rows:
        throughput = row.get("throughput_requests_per_s")
        row["throughput_gain_vs_concurrency_4"] = (
            throughput / baseline_throughput if throughput is not None and baseline_throughput else None
        )
    report = {
        "watermark": "INFRASTRUCTURE BENCHMARK — NOT SCIENTIFIC DATA",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": config.agent.model,
        "backend": "deepseek_direct",
        "thinking": "disabled",
        "jobs_per_level": jobs,
        "nominal_jobs_total": jobs * len(levels),
        "max_physical_attempts_total": max_physical_attempts,
        "max_cost_usd_total": max_cost_usd,
        "levels": rows,
        "recommended_probe_concurrency": recommendation,
        "recommendation_reason": recommendation_reason,
        "recommendation_rule": "exclude failures/429/timeouts, then stop at a visible throughput/latency knee",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, output)
    return report


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Opt-in DeepSeek Direct infrastructure benchmark")
    parser.add_argument("--config", default=str(REPO_ROOT / "configs/research/replication_private.yaml"))
    parser.add_argument("--concurrency", default="4,8,16,32")
    parser.add_argument("--jobs-per-level", type=int, default=32)
    parser.add_argument("--max-cost-usd", type=float, default=0.25)
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "reports/infrastructure-benchmarks"))
    parser.add_argument("--max-physical-attempts", type=int, default=128)
    parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    levels = _parse_levels(args.concurrency)
    if args.jobs_per_level < 1:
        parser.error("--jobs-per-level must be positive")
    if args.max_physical_attempts < 1:
        parser.error("--max-physical-attempts must be positive")
    if not args.confirm_real:
        print("INFRASTRUCTURE BENCHMARK PLAN (no model calls)")
        print(f"levels={list(levels)} jobs_per_level={args.jobs_per_level} max_cost_usd={args.max_cost_usd} max_physical_attempts={args.max_physical_attempts}")
        print("Add --confirm-real only when you explicitly want live paid requests.")
        return
    report = asyncio.run(_run_live(args.config, levels, args.jobs_per_level, args.max_cost_usd, args.max_physical_attempts, _resolve_path(args.output_dir)))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

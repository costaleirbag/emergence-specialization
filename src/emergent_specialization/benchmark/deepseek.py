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
    }


async def _run_live(config_path: str, levels: tuple[int, ...], jobs: int, max_cost_usd: float | None, output: Path) -> dict[str, Any]:
    config = load_config(config_path)
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
        for level in levels:
            row = await _run_level(
                    backend,
                    level=level,
                    jobs=jobs,
                    max_cost_usd=remaining_budget,
                    input_rate=config.cost.input_per_million_tokens,
                    cached_rate=config.cost.cached_input_per_million_tokens,
                    output_rate=config.cost.output_per_million_tokens,
                )
            rows.append(row)
            if remaining_budget is not None and row.get("observed_cost_usd") is not None:
                remaining_budget = max(0.0, remaining_budget - float(row["observed_cost_usd"]))
    finally:
        await backend.close()
    viable = [row for row in rows if row["failures"] == 0 and row["rate_limit_429_count"] == 0]
    recommendation = max(viable, key=lambda row: row["concurrency"])["concurrency"] if viable else None
    report = {
        "watermark": "INFRASTRUCTURE BENCHMARK — NOT SCIENTIFIC DATA",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": config.agent.model,
        "backend": "deepseek_direct",
        "thinking": "disabled",
        "jobs_per_level": jobs,
        "max_cost_usd_total": max_cost_usd,
        "levels": rows,
        "recommended_probe_concurrency": recommendation,
        "recommendation_rule": "highest tested level with zero failures and zero HTTP 429; inspect p95 before adopting",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Opt-in DeepSeek Direct infrastructure benchmark")
    parser.add_argument("--config", default="configs/research/replication_private.yaml")
    parser.add_argument("--concurrency", default="4,8,16,32")
    parser.add_argument("--jobs-per-level", type=int, default=32)
    parser.add_argument("--max-cost-usd", type=float, default=0.25)
    parser.add_argument("--output-dir", default="reports/infrastructure-benchmarks")
    parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    levels = _parse_levels(args.concurrency)
    if args.jobs_per_level < 1:
        parser.error("--jobs-per-level must be positive")
    if not args.confirm_real:
        print("INFRASTRUCTURE BENCHMARK PLAN (no model calls)")
        print(f"levels={list(levels)} jobs_per_level={args.jobs_per_level} max_cost_usd={args.max_cost_usd}")
        print("Add --confirm-real only when you explicitly want live paid requests.")
        return
    report = asyncio.run(_run_live(args.config, levels, args.jobs_per_level, args.max_cost_usd, Path(args.output_dir)))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

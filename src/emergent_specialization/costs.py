"""Token-usage normalization and opt-in inference cost accounting.

Providers are not required to expose billing information.  This module keeps
that distinction explicit: token totals are reported only when the provider
actually supplies them, and a monetary value is labelled as an estimate based
on rates supplied in the run configuration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


_MISSING = object()


def _number(value: Any) -> int | float | None:
    """Return a finite numeric token count, or ``None`` for unknown values."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value if value >= 0 else None
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed if parsed >= 0 and parsed.is_integer() else None
    return None


def _first_number(mapping: Mapping[str, Any], *keys: str) -> int | float | None:
    for key in keys:
        value = _number(mapping.get(key, _MISSING))
        if value is not None:
            return value
    return None


def normalize_token_usage(usage: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Normalize common OpenAI/DeepSeek usage field names.

    The raw provider payload is retained in ``events.jsonl``.  The normalized
    result is only used for aggregation and never replaces that provenance.
    """
    if not isinstance(usage, Mapping):
        return None

    input_tokens = _first_number(
        usage, "input_tokens", "prompt_tokens", "inputTokens", "promptTokens", "input"
    )
    output_tokens = _first_number(
        usage, "output_tokens", "completion_tokens", "outputTokens", "completionTokens", "output"
    )
    cached_input_tokens = _first_number(
        usage,
        "cached_input_tokens",
        "cache_read_input_tokens",
        "prompt_cache_hit_tokens",
        "cached_tokens",
        "cachedInputTokens",
        "cacheRead",
    )
    reasoning_tokens = _first_number(usage, "reasoning_tokens", "reasoningTokens")
    total_tokens = _first_number(usage, "total_tokens", "totalTokens")

    prompt_details = usage.get("prompt_tokens_details") or usage.get("promptTokensDetails")
    if isinstance(prompt_details, Mapping) and cached_input_tokens is None:
        cached_input_tokens = _first_number(prompt_details, "cached_tokens", "cached_input_tokens")
    completion_details = usage.get("completion_tokens_details") or usage.get("completionTokensDetails")
    if isinstance(completion_details, Mapping) and reasoning_tokens is None:
        reasoning_tokens = _first_number(completion_details, "reasoning_tokens", "reasoningTokens")

    result: dict[str, Any] = {}
    for key, value in (
        ("input_tokens", input_tokens),
        ("cached_input_tokens", cached_input_tokens),
        ("output_tokens", output_tokens),
        ("reasoning_tokens", reasoning_tokens),
        ("total_tokens", total_tokens),
    ):
        if value is not None:
            result[key] = value
    if "total_tokens" not in result and input_tokens is not None and output_tokens is not None:
        result["total_tokens"] = input_tokens + output_tokens

    provider_cost = usage.get("cost")
    if isinstance(provider_cost, Mapping):
        normalized_cost: dict[str, int | float] = {}
        for key, aliases in {
            "input": ("input", "input_cost"),
            "output": ("output", "output_cost"),
            "cache_read": ("cacheRead", "cache_read", "cache_read_cost"),
            "cache_write": ("cacheWrite", "cache_write", "cache_write_cost"),
            "total": ("total", "total_cost"),
        }.items():
            value = _first_number(provider_cost, *aliases)
            if value is not None:
                normalized_cost[key] = value
        if normalized_cost:
            result["provider_cost"] = normalized_cost
    return result or None


def _sum_complete(values: list[dict[str, int | float]], key: str) -> int | float | None:
    if not values or any(key not in value for value in values):
        return None
    return sum(value[key] for value in values)


def summarize_usage(
    usages: Iterable[Mapping[str, Any] | None],
    *,
    currency: str = "USD",
    input_per_million_tokens: float | None = None,
    cached_input_per_million_tokens: float | None = None,
    output_per_million_tokens: float | None = None,
) -> dict[str, Any]:
    """Aggregate usage and calculate an optional configured cost estimate."""
    raw_usages = list(usages)
    normalized = [normalize_token_usage(usage) for usage in raw_usages]
    usable = [value for value in normalized if value is not None]
    calls_with_usage = len(usable)
    calls_total = len(raw_usages)
    usage_complete = calls_total > 0 and calls_with_usage == calls_total
    aggregate = {
        "input_tokens": _sum_complete(usable, "input_tokens") if usage_complete else None,
        "cached_input_tokens": _sum_complete(usable, "cached_input_tokens") if usage_complete else None,
        "output_tokens": _sum_complete(usable, "output_tokens") if usage_complete else None,
        "reasoning_tokens": _sum_complete(usable, "reasoning_tokens") if usage_complete else None,
        "total_tokens": _sum_complete(usable, "total_tokens") if usage_complete else None,
    }
    if usage_complete and aggregate["input_tokens"] is not None and aggregate["cached_input_tokens"] is not None:
        aggregate["cache_miss_input_tokens"] = max(
            aggregate["input_tokens"] - aggregate["cached_input_tokens"], 0
        )
        denominator = aggregate["cached_input_tokens"] + aggregate["cache_miss_input_tokens"]
        aggregate["cache_hit_ratio"] = (
            aggregate["cached_input_tokens"] / denominator if denominator else None
        )
    else:
        aggregate["cache_miss_input_tokens"] = None
        aggregate["cache_hit_ratio"] = None
    provider_cost_values = [value.get("provider_cost") for value in usable]
    provider_cost_complete = bool(usage_complete and provider_cost_values and all(provider_cost_values))
    reported_cost: dict[str, int | float] = {}
    if provider_cost_complete:
        for key in ("input", "output", "cache_read", "cache_write", "total"):
            values = [cost.get(key) for cost in provider_cost_values]
            if all(value is not None for value in values):
                reported_cost[key] = sum(value for value in values if value is not None)

    pricing = {
        "currency": currency,
        "input_per_million_tokens": input_per_million_tokens,
        "cached_input_per_million_tokens": cached_input_per_million_tokens,
        "output_per_million_tokens": output_per_million_tokens,
    }
    estimated_cost: float | None = None
    if "total" in reported_cost:
        status = "provider_reported"
    elif calls_total == 0 or calls_with_usage == 0:
        status = "unavailable"
    elif not usage_complete:
        status = "partial_usage"
    elif aggregate["input_tokens"] is None or aggregate["output_tokens"] is None:
        status = "missing_input_or_output_tokens"
    elif input_per_million_tokens is None or output_per_million_tokens is None:
        status = "pricing_not_configured"
    elif aggregate["cached_input_tokens"] not in (None, 0) and cached_input_per_million_tokens is None:
        status = "cached_input_pricing_not_configured"
    else:
        cached = aggregate["cached_input_tokens"] or 0
        uncached = max(aggregate["input_tokens"] - cached, 0)
        input_cost = uncached * input_per_million_tokens / 1_000_000
        cached_cost = cached * (cached_input_per_million_tokens or input_per_million_tokens) / 1_000_000
        output_cost = aggregate["output_tokens"] * output_per_million_tokens / 1_000_000
        estimated_cost = input_cost + cached_cost + output_cost
        status = "estimated"

    return {
        "status": status,
        "currency": currency,
        "calls_total": calls_total,
        "calls_with_usage": calls_with_usage,
        "usage_coverage": (calls_with_usage / calls_total) if calls_total else 0.0,
        **aggregate,
        "pricing": pricing,
        "reported_cost": reported_cost.get("total"),
        "reported_cost_breakdown": reported_cost or None,
        "estimated_cost": estimated_cost,
    }


def estimate_usage_cost(
    usage: Mapping[str, Any] | None,
    *,
    input_per_million_tokens: float | None,
    cached_input_per_million_tokens: float | None,
    output_per_million_tokens: float | None,
) -> float | None:
    """Estimate one attempt's USD cost when all required usage/rates exist."""
    normalized = normalize_token_usage(usage)
    if not normalized or normalized.get("input_tokens") is None or normalized.get("output_tokens") is None:
        return None
    if input_per_million_tokens is None or output_per_million_tokens is None:
        return None
    cached = normalized.get("cached_input_tokens") or 0
    cache_rate = cached_input_per_million_tokens if cached_input_per_million_tokens is not None else input_per_million_tokens
    uncached = max(float(normalized["input_tokens"]) - float(cached), 0.0)
    return (
        uncached * input_per_million_tokens / 1_000_000
        + float(cached) * cache_rate / 1_000_000
        + float(normalized["output_tokens"]) * output_per_million_tokens / 1_000_000
    )

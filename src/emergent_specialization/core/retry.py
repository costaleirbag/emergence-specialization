"""Deterministic, injectable retry backoff helpers."""

from __future__ import annotations

import hashlib
import random


def retry_delay(
    attempt: int,
    *,
    base_s: float = 1.0,
    max_s: float = 30.0,
    jitter_s: float = 0.25,
    logical_id: str = "",
    retry_after_s: float | None = None,
) -> float:
    """Return a reproducible full-jitter delay without sleeping."""
    if retry_after_s is not None:
        return max(0.0, float(retry_after_s))
    cap = min(float(max_s), float(base_s) * (2 ** max(0, attempt)))
    digest = hashlib.sha256(f"{logical_id}:{attempt}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    # Full jitter keeps a thundering herd from synchronizing while remaining
    # deterministic for a given logical completion and attempt.
    return min(float(max_s), max(0.0, rng.uniform(0.0, cap) + rng.uniform(0.0, max(0.0, jitter_s))))

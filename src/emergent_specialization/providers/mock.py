"""Deterministic fake backend used by tests and dry runs.

It reads only the model-visible controlled memory and task prompt.  It fits a
small modular rule from feedback examples, which lets dry runs exercise the
private-feedback mechanism without contacting an API or reading hidden rules.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from itertools import product
from typing import Any

from emergent_specialization.core.models import BackendResponse


_MEMORY_RE = re.compile(r"CONTROLLED_MEMORY_JSON:\n(.*?)\n\nCURRENT_TASK:", re.DOTALL)
_TASK_RE = re.compile(r"World ([A-Z]+).*?x = (-?\d+).*?y = (-?\d+)", re.DOTALL)


class MockBackend:
    """A reproducible stand-in; it is not a proxy for DeepSeek behavior."""

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "mock",
            "description": "Deterministic modular-rule learner; no network or hidden-rule access.",
        }

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        model_parameters: dict[str, Any],
    ) -> BackendResponse:
        started = time.perf_counter()
        try:
            memory = self._parse_memory(user_prompt)
            world, x, y = self._parse_task(user_prompt)
            answer, confidence = self._predict(world, x, y, memory)
            raw = json.dumps({"answer": answer, "confidence": confidence}, separators=(",", ":"))
            return BackendResponse(raw_response=raw, latency_s=time.perf_counter() - started)
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            return BackendResponse(
                raw_response=None,
                latency_s=time.perf_counter() - started,
                error=f"Mock backend failure: {type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _parse_memory(prompt: str) -> list[dict[str, Any]]:
        match = _MEMORY_RE.search(prompt)
        if not match:
            raise ValueError("controlled memory delimiter is missing")
        parsed = json.loads(match.group(1))
        if not isinstance(parsed, list):
            raise ValueError("controlled memory is not a list")
        return parsed

    @staticmethod
    def _parse_task(prompt: str) -> tuple[str, int, int]:
        match = _TASK_RE.search(prompt)
        if not match:
            raise ValueError("task fields are missing")
        return match.group(1), int(match.group(2)), int(match.group(3))

    def _predict(self, world: str, x: int, y: int, memory: list[dict[str, Any]]) -> tuple[int, float]:
        relevant = [
            item
            for item in memory
            if item.get("world") == world
            and isinstance(item.get("x"), int)
            and isinstance(item.get("y"), int)
            and isinstance(item.get("correct_answer"), int)
        ]
        candidates = []
        for a, b, c in product(range(7), repeat=3):
            if all((a * item["x"] + b * item["y"] + c) % 7 == item["correct_answer"] for item in relevant):
                candidates.append((a, b, c))

        outputs = Counter((a * x + b * y + c) % 7 for a, b, c in candidates)
        if not outputs:  # Cannot occur for well-formed environment feedback.
            return self._fallback(world, x, y), 0.0
        most_common = max(outputs.values())
        answer = min(output for output, count in outputs.items() if count == most_common)
        certainty = most_common / len(candidates)
        # A deliberately conservative confidence curve: the initial prompt is
        # identical for every agent; differentiated memory is the only cause of
        # later confidence differences in a dry run.
        confidence = round(min(0.95, 0.20 + 0.75 * certainty), 6)
        return answer, confidence

    @staticmethod
    def _fallback(world: str, x: int, y: int) -> int:
        # Stable task-dependent fallback, intentionally independent of agent ID.
        return (sum(ord(char) for char in world) + 3 * x + 5 * y) % 7

"""Auditable, bounded memory selection with no retrieval side effects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from .models import Experience


@dataclass(frozen=True)
class MemoryPolicy:
    strategy: str = "recent_k"
    k: int = 8

    def __post_init__(self) -> None:
        if self.strategy not in {"recent_k", "all"}:
            raise ValueError("memory strategy must be 'recent_k' or 'all'")
        if self.k < 0:
            raise ValueError("memory k must be non-negative")

    def select(self, memory: Sequence[Experience]) -> list[Experience]:
        if self.strategy == "all":
            return list(memory)
        if self.k == 0:
            return []
        return list(memory[-self.k :])

    def render(self, memory: Sequence[Experience]) -> tuple[str, list[dict[str, object]]]:
        selected = self.select(memory)
        records = [experience.prompt_dict() for experience in selected]
        encoded = json.dumps(records, sort_keys=True, separators=(",", ":"))
        return encoded, records

"""Confidence router with reproducible random ties and optional exploration."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from emergent_specialization.core.models import AgentResponse


@dataclass(frozen=True)
class RouterDecision:
    selected_agent_id: str
    selection_mode: str
    tied_agent_ids: tuple[str, ...]


class ConfidenceRouter:
    def __init__(self, epsilon: float = 0.0) -> None:
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must lie in [0, 1]")
        self.epsilon = epsilon

    def select(self, responses: Sequence[AgentResponse], rng: random.Random) -> RouterDecision:
        if not responses:
            raise ValueError("Cannot route without a valid response")
        ordered = sorted(responses, key=lambda response: response.agent_id)
        if self.epsilon > 0 and rng.random() < self.epsilon:
            selected = rng.choice(ordered)
            return RouterDecision(selected.agent_id, "epsilon_random", (selected.agent_id,))

        max_confidence = max(response.confidence for response in ordered)
        tied = tuple(response.agent_id for response in ordered if response.confidence == max_confidence)
        return RouterDecision(rng.choice(tied), "confidence", tied)

    @staticmethod
    def deterministic_probe_choice(responses: Sequence[AgentResponse]) -> str | None:
        """Route a fixed probe without epsilon or random tie variation."""
        if not responses:
            return None
        max_confidence = max(response.confidence for response in responses)
        return min(response.agent_id for response in responses if response.confidence == max_confidence)

    def probe_choice(self, responses: Sequence[AgentResponse], rng: random.Random) -> str | None:
        """Choose a diagnostic probe route using the confidence policy.

        This remains deterministic for a fixed response set.  The method is an
        instance hook so the experiment can use the same interface for the
        random-routing ablation without changing interaction semantics.
        """
        return self.deterministic_probe_choice(responses)


class RandomRouter:
    """Uniform router used only by the pre-specified routing ablation.

    Agent IDs are sorted before sampling so asynchronous response order and
    Python list order cannot bias the result.  Exactly one RNG draw is made
    per selection, independent of confidence values.
    """

    def select(self, responses: Sequence[AgentResponse], rng: random.Random) -> RouterDecision:
        if not responses:
            raise ValueError("Cannot route without a valid response")
        ordered = tuple(sorted(responses, key=lambda response: response.agent_id))
        selected = rng.choice(ordered)
        return RouterDecision(
            selected_agent_id=selected.agent_id,
            selection_mode="random",
            tied_agent_ids=tuple(response.agent_id for response in ordered),
        )

    def probe_choice(self, responses: Sequence[AgentResponse], rng: random.Random) -> str | None:
        if not responses:
            return None
        ordered = tuple(sorted(responses, key=lambda response: response.agent_id))
        return rng.choice(ordered).agent_id

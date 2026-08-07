"""A small reinforcement-driven allocation sandbox.

This module is intentionally separate from the LLM experiment. It is useful for
checking whether a proposed feedback mechanism can create differentiated skill
profiles before spending provider calls; it is not fitted to observed runs.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MinimalModelConfig:
    num_agents: int = 4
    num_tasks: int = 4
    beta: float = 3.0
    learning_rate: float = 0.2
    private_probability: float = 1.0
    exploration: float = 0.0
    rounds: int = 40
    seed: int = 1

    def __post_init__(self) -> None:
        if self.num_agents < 2 or self.num_tasks < 1:
            raise ValueError("minimal model requires at least two agents and one task")
        if self.beta < 0 or self.learning_rate < 0 or self.learning_rate > 1:
            raise ValueError("beta must be non-negative and learning_rate must be in [0, 1]")
        if not 0.0 <= self.private_probability <= 1.0:
            raise ValueError("private_probability must be in [0, 1]")
        if not 0.0 <= self.exploration <= 1.0:
            raise ValueError("exploration must be in [0, 1]")
        if self.rounds < 0:
            raise ValueError("rounds must be non-negative")


@dataclass(frozen=True)
class MinimalModelResult:
    selections: tuple[dict[str, Any], ...]
    skills: tuple[tuple[tuple[float, ...], ...], ...]

    @property
    def final_skills(self) -> tuple[tuple[float, ...], ...]:
        return self.skills[-1] if self.skills else ()


def _softmax(values: list[float], beta: float) -> list[float]:
    logits = [beta * value for value in values]
    maximum = max(logits)
    weights = [math.exp(value - maximum) for value in logits]
    total = sum(weights)
    return [weight / total for weight in weights]


def _sample(rng: random.Random, probabilities: list[float]) -> int:
    draw = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if draw <= cumulative:
            return index
    return len(probabilities) - 1


def simulate(config: MinimalModelConfig) -> MinimalModelResult:
    rng = random.Random(config.seed)
    skills = [[0.5 for _ in range(config.num_tasks)] for _ in range(config.num_agents)]
    snapshots: list[tuple[tuple[float, ...], ...]] = [tuple(tuple(row) for row in skills)]
    selections: list[dict[str, Any]] = []
    for round_id in range(1, config.rounds + 1):
        task = rng.randrange(config.num_tasks)
        probabilities = _softmax([skills[agent][task] for agent in range(config.num_agents)], config.beta)
        probabilities = [
            (1.0 - config.exploration) * probability + config.exploration / config.num_agents
            for probability in probabilities
        ]
        selected = _sample(rng, probabilities)
        correct = rng.random() < skills[selected][task]
        private = rng.random() < config.private_probability
        recipients = [selected] if private else list(range(config.num_agents))
        if correct:
            for recipient in recipients:
                skills[recipient][task] += config.learning_rate * (1.0 - skills[recipient][task])
        else:
            for recipient in recipients:
                skills[recipient][task] -= config.learning_rate * skills[recipient][task]
        selections.append(
            {
                "round": round_id,
                "task": task,
                "selected_agent": selected,
                "probabilities": probabilities,
                "correct": correct,
                "private_feedback": private,
                "recipients": recipients,
            }
        )
        snapshots.append(tuple(tuple(row) for row in skills))
    return MinimalModelResult(tuple(selections), tuple(snapshots))

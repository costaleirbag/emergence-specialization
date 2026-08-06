"""Deterministic hidden modular worlds controlled exclusively by Python."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final, Iterable

from .models import Task


MODULUS: Final[int] = 7

# These coefficients must never be formatted into a model prompt.  They are
# environment-only facts and may appear in experimenter-side source/logs.
HIDDEN_RULES: Final[dict[str, tuple[int, int, int]]] = {
    "ALPHA": (2, 1, 1),
    "BETA": (1, 3, 2),
    "GAMMA": (4, 2, 0),
    "DELTA": (3, 5, 4),
}


@dataclass(frozen=True)
class HiddenWorldEnvironment:
    worlds: tuple[str, ...] = tuple(HIDDEN_RULES)
    x_min: int = 0
    x_max: int = 20

    def __post_init__(self) -> None:
        unknown = set(self.worlds) - set(HIDDEN_RULES)
        if unknown:
            raise ValueError(f"Unknown worlds: {sorted(unknown)}")
        if self.x_min > self.x_max:
            raise ValueError("x_min must not exceed x_max")

    def answer_for(self, world: str, x: int, y: int) -> int:
        a, b, c = HIDDEN_RULES[world]
        return (a * x + b * y + c) % MODULUS

    def make_task(self, world: str, x: int, y: int, task_id: str | None = None) -> Task:
        if world not in self.worlds:
            raise ValueError(f"World {world!r} is not enabled")
        return Task(
            world=world,
            x=x,
            y=y,
            correct_answer=self.answer_for(world, x, y),
            task_id=task_id,
        )

    def sample_task(self, rng: random.Random, *, task_id: str | None = None) -> Task:
        world = rng.choice(self.worlds)
        x = rng.randint(self.x_min, self.x_max)
        y = rng.randint(self.x_min, self.x_max)
        return self.make_task(world, x, y, task_id=task_id)

    def evaluate(self, task: Task, answer: int) -> bool:
        return answer == task.correct_answer


def task_prompt(task: Task) -> str:
    """Render only public task information, with no rule coefficients/answer."""
    choices = "\n".join(f"{letter}) {value}" for letter, value in zip("ABCDEFG", range(MODULUS)))
    return (
        f"You are solving a task from World {task.world}.\n\n"
        "Input:\n"
        f"x = {task.x}\n"
        f"y = {task.y}\n\n"
        "The hidden world follows a fixed rule that you are not given directly.\n"
        "What is the output?\n\n"
        f"{choices}"
    )


def enabled_worlds(worlds: Iterable[str]) -> tuple[str, ...]:
    return tuple(worlds)

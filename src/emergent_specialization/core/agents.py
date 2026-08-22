"""Identical experimental agents with Python-owned memory only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Sequence

from emergent_specialization.core.environment import task_prompt
from emergent_specialization.core.memory import MemoryPolicy
from emergent_specialization.core.models import Experience, Task


DEFAULT_SYSTEM_PROMPT = """You are one member of a society solving repeated tasks from several hidden worlds.

All worlds obey stable but initially unknown rules.

Use your private memory of previous tasks and feedback to improve future answers.

For each task return:
1. your predicted answer;
2. a confidence between 0 and 1.

Do not assume that you have a predefined specialty.
Do not invent a social role.
Infer useful regularities only from your own observed experience."""


@dataclass
class ExperimentalAgent:
    """An opaque host-side ID and a list of controlled feedback experiences."""

    agent_id: str
    memory: list[Experience] = field(default_factory=list)

    def observe(self, experience: Experience) -> None:
        self.memory.append(experience)

    def prompt_parts(
        self,
        task: Task,
        policy: MemoryPolicy,
        *,
        memory_snapshot: Sequence[Experience] | None = None,
    ) -> tuple[str, list[dict[str, object]]]:
        """Create the user message without placing agent_id in model-visible text."""
        source_memory = self.memory if memory_snapshot is None else memory_snapshot
        memory_json, inserted = policy.render(source_memory)
        message = (
            "Your controlled feedback memory is below. It is the only source of past "
            "experience available for this task.\n"
            "CONTROLLED_MEMORY_JSON:\n"
            f"{memory_json}\n\n"
            "CURRENT_TASK:\n"
            f"{task_prompt(task)}\n\n"
            "Return only a JSON object matching exactly this schema, with no Markdown:\n"
            '{"answer": <integer 0..6>, "confidence": <number 0..1>}'
        )
        return message, inserted


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def assert_initial_symmetry(
    agents: Sequence[ExperimentalAgent], system_prompt: str, *, require_empty_memory: bool = True
) -> None:
    if not agents:
        raise ValueError("At least one agent is required")
    if require_empty_memory and any(agent.memory for agent in agents):
        raise AssertionError("Experimental agents must begin with empty memory")
    if not system_prompt:
        raise AssertionError("All agents must share a non-empty base system prompt")


def render_public_task_json(task: Task) -> str:
    """Used by MockBackend; contains only fields the real prompt reveals."""
    return json.dumps(task.public_dict(), sort_keys=True, separators=(",", ":"))

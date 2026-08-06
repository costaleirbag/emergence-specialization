"""Small, explicit data structures used by the scientific harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    """A task whose answer is held only by the experiment environment."""

    world: str
    x: int
    y: int
    correct_answer: int
    task_id: str | None = None

    def public_dict(self) -> dict[str, Any]:
        """Return the task fields that may be shown to a model."""
        return {"world": self.world, "x": self.x, "y": self.y, "choices": list(range(7))}

    def experimenter_dict(self) -> dict[str, Any]:
        """Return all fields for logs belonging to the experimenter."""
        data = asdict(self)
        return data


@dataclass(frozen=True)
class Experience:
    """One selected task and its observed feedback."""

    round_id: int
    world: str
    x: int
    y: int
    prediction: int
    confidence: float
    correct_answer: int
    was_correct: bool

    def prompt_dict(self) -> dict[str, Any]:
        """The complete, controlled feedback item included in memory context."""
        return asdict(self)


@dataclass(frozen=True)
class AgentResponse:
    agent_id: str
    answer: int
    confidence: float


@dataclass(frozen=True)
class BackendResponse:
    """Unparsed result returned by a provider adapter."""

    raw_response: str | None
    latency_s: float
    token_usage: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class InferenceRecord:
    """One physical model/API attempt, including retries and parse failures."""

    phase: str
    round_id: int | None
    checkpoint: int | None
    probe_index: int | None
    agent_id: str
    attempt: int
    retry_count: int
    model: str
    model_parameters: dict[str, Any]
    task: dict[str, Any]
    memory_inserted: list[dict[str, Any]]
    prompt_hash: str
    system_prompt_hash: str
    raw_model_response: str | None
    parsed_answer: int | None
    confidence: float | None
    latency_s: float
    token_usage: dict[str, Any] | None
    error: str | None


@dataclass(frozen=True)
class ProbeObservation:
    probe_index: int
    task: Task
    response: AgentResponse | None
    error: str | None = None

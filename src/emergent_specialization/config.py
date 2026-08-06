"""Declarative configuration and CLI-safe overrides."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from .agents import DEFAULT_SYSTEM_PROMPT


@dataclass(frozen=True)
class ExperimentSettings:
    num_agents: int = 4
    num_rounds: int = 80
    checkpoints: tuple[int, ...] = (0, 20, 40, 60, 80)
    seed: int = 1
    task_seed: int | None = None
    router_seed: int | None = None
    max_concurrency: int = 4
    technical_retries: int = 1
    console_summary: bool = True

    def __post_init__(self) -> None:
        if self.num_agents < 2:
            raise ValueError("num_agents must be at least 2")
        if self.num_rounds < 0:
            raise ValueError("num_rounds must be non-negative")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if self.technical_retries < 0:
            raise ValueError("technical_retries must be non-negative")
        if any(checkpoint < 0 or checkpoint > self.num_rounds for checkpoint in self.checkpoints):
            raise ValueError("checkpoints must lie between 0 and num_rounds")
        if tuple(sorted(set(self.checkpoints))) != self.checkpoints:
            raise ValueError("checkpoints must be sorted and unique")


@dataclass(frozen=True)
class EnvironmentSettings:
    worlds: tuple[str, ...] = ("ALPHA", "BETA", "GAMMA", "DELTA")
    x_min: int = 0
    x_max: int = 20


@dataclass(frozen=True)
class AgentSettings:
    backend: str = "omp"
    model: str = "deepseek/deepseek-v4-flash"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    memory_strategy: str = "recent_k"
    memory_k: int = 8
    thinking: str = "off"
    omp_executable: str = "omp"
    omp_timeout_s: float = 120.0
    omp_working_directory: str | None = None
    # These are logged as experimental intent. OMP 17.2.10 does not expose
    # documented CLI/RPC switches for them, so OMPBackend never pretends to set
    # them. A future direct backend can use the same fields.
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.backend not in {"omp", "mock"}:
            raise ValueError("agent backend must be 'omp' or 'mock'")
        if self.memory_strategy not in {"recent_k", "all"}:
            raise ValueError("memory_strategy must be recent_k or all")
        if self.memory_k < 0:
            raise ValueError("memory_k must be non-negative")
        if self.thinking not in {"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto"}:
            raise ValueError("thinking must be one of OMP's documented thinking levels")
        if self.omp_timeout_s <= 0:
            raise ValueError("omp_timeout_s must be positive")


@dataclass(frozen=True)
class RouterSettings:
    strategy: str = "confidence"
    epsilon: float = 0.0

    def __post_init__(self) -> None:
        if self.strategy != "confidence":
            raise ValueError("only confidence routing is implemented")
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")


@dataclass(frozen=True)
class ConditionSettings:
    memory_mode: str = "private"

    def __post_init__(self) -> None:
        if self.memory_mode not in {"private", "shared", "no_memory"}:
            raise ValueError("memory_mode must be private, shared, or no_memory")


@dataclass(frozen=True)
class LoggingSettings:
    output_dir: str = "data/runs"
    probe_set_path: str = "data/probe_set.json"


@dataclass(frozen=True)
class CostSettings:
    """Optional provider pricing used only for transparent cost estimates.

    Rates are expressed in the configured currency per one million tokens. A
    run remains valid with all rates unset; its summary then reports usage and
    explicitly marks monetary cost as unavailable.
    """

    currency: str = "USD"
    input_per_million_tokens: float | None = None
    cached_input_per_million_tokens: float | None = None
    output_per_million_tokens: float | None = None

    def __post_init__(self) -> None:
        if not self.currency or not self.currency.strip():
            raise ValueError("cost currency must not be empty")
        for name, value in (
            ("input_per_million_tokens", self.input_per_million_tokens),
            ("cached_input_per_million_tokens", self.cached_input_per_million_tokens),
            ("output_per_million_tokens", self.output_per_million_tokens),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative or null")


@dataclass(frozen=True)
class RunConfig:
    experiment: ExperimentSettings = field(default_factory=ExperimentSettings)
    environment: EnvironmentSettings = field(default_factory=EnvironmentSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    router: RouterSettings = field(default_factory=RouterSettings)
    condition: ConditionSettings = field(default_factory=ConditionSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    cost: CostSettings = field(default_factory=CostSettings)
    source_path: str | None = None
    source_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def overridden(
        self,
        *,
        num_rounds: int | None = None,
        seed: int | None = None,
        output_dir: str | None = None,
        backend: str | None = None,
    ) -> "RunConfig":
        experiment = self.experiment
        if num_rounds is not None:
            checkpoints = tuple(checkpoint for checkpoint in experiment.checkpoints if checkpoint <= num_rounds)
            if 0 not in checkpoints:
                checkpoints = (0, *checkpoints)
            if num_rounds not in checkpoints:
                checkpoints = tuple(sorted((*checkpoints, num_rounds)))
            experiment = replace(experiment, num_rounds=num_rounds, checkpoints=checkpoints)
        if seed is not None:
            experiment = replace(experiment, seed=seed, task_seed=None, router_seed=None)
        agent = replace(self.agent, backend=backend) if backend is not None else self.agent
        logging = replace(self.logging, output_dir=output_dir) if output_dir is not None else self.logging
        return replace(self, experiment=experiment, agent=agent, logging=logging)


def _mapping(value: Any, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{section} must be a YAML mapping")
    return dict(value)


def load_config(path: str | Path) -> RunConfig:
    config_path = Path(path)
    raw_text = config_path.read_text(encoding="utf-8")
    raw = yaml.safe_load(raw_text)
    raw = _mapping(raw, "root")

    experiment = _mapping(raw.get("experiment"), "experiment")
    environment = _mapping(raw.get("environment"), "environment")
    agent = _mapping(raw.get("agent"), "agent")
    router = _mapping(raw.get("router"), "router")
    condition = _mapping(raw.get("condition"), "condition")
    logging = _mapping(raw.get("logging"), "logging")
    cost = _mapping(raw.get("cost"), "cost")

    if "checkpoints" in experiment:
        experiment["checkpoints"] = tuple(experiment["checkpoints"])
    if "worlds" in environment:
        environment["worlds"] = tuple(environment["worlds"])

    import hashlib

    return RunConfig(
        experiment=ExperimentSettings(**experiment),
        environment=EnvironmentSettings(**environment),
        agent=AgentSettings(**agent),
        router=RouterSettings(**router),
        condition=ConditionSettings(**condition),
        logging=LoggingSettings(**logging),
        cost=CostSettings(**cost),
        source_path=str(config_path),
        source_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
    )

"""Declarative configuration and CLI-safe overrides."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

import yaml

from emergent_specialization.core.agents import DEFAULT_SYSTEM_PROMPT


@dataclass(frozen=True)
class ExperimentSettings:
    num_agents: int = 4
    num_rounds: int = 80
    checkpoints: tuple[int, ...] = (0, 20, 40, 60, 80)
    seed: int = 1
    task_seed: int | None = None
    router_seed: int | None = None
    feedback_seed: int | None = None
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
        if self.backend not in {"omp", "mock", "deepseek_direct"}:
            raise ValueError("agent backend must be 'omp', 'deepseek_direct', or 'mock'")
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
        if self.strategy not in {"confidence", "random"}:
            raise ValueError("router strategy must be 'confidence' or 'random'")
        if self.strategy == "random" and self.epsilon != 0.0:
            raise ValueError("random routing does not accept epsilon exploration")
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")


@dataclass(frozen=True)
class ConditionSettings:
    memory_mode: str = "private"

    def __post_init__(self) -> None:
        if self.memory_mode not in {"private", "shared", "no_memory"}:
            raise ValueError("memory_mode must be private, shared, or no_memory")


@dataclass(frozen=True)
class FeedbackSettings:
    """Information-locality policy for selected feedback.

    ``condition.memory_mode`` remains the legacy public schema. This separate
    policy lets future studies interpolate between the existing private and
    shared endpoints without changing those configs.
    """

    mode: str = "private"
    private_probability: float | None = None
    schedule: tuple[tuple[int, float], ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in {"private", "shared", "probabilistic", "none"}:
            raise ValueError("feedback mode must be private, shared, probabilistic, or none")
        if self.mode == "probabilistic":
            if self.private_probability is None:
                raise ValueError("probabilistic feedback requires private_probability")
            if not 0.0 <= self.private_probability <= 1.0:
                raise ValueError("private_probability must be in [0, 1]")
        elif self.private_probability is not None and not 0.0 <= self.private_probability <= 1.0:
            raise ValueError("private_probability must be in [0, 1]")
        if tuple(sorted(self.schedule)) != self.schedule:
            raise ValueError("feedback schedule must be sorted by round")
        if len({round_id for round_id, _ in self.schedule}) != len(self.schedule):
            raise ValueError("feedback schedule must not repeat a round")
        if any(round_id < 1 or not 0.0 <= probability <= 1.0 for round_id, probability in self.schedule):
            raise ValueError("feedback schedule rounds must be positive and probabilities in [0, 1]")

    @classmethod
    def from_legacy(cls, memory_mode: str) -> "FeedbackSettings":
        return cls(mode={"no_memory": "none"}.get(memory_mode, memory_mode))

    def as_label(self) -> str:
        if self.mode == "probabilistic":
            return f"probabilistic-p{self.private_probability:g}"
        return self.mode

    def probability_at(self, round_id: int) -> float:
        """Return the last scheduled private probability at a round."""
        if self.mode == "probabilistic":
            current = self.private_probability or 0.0
        elif self.mode == "private":
            current = 1.0
        else:
            current = 0.0
        for start, probability in self.schedule:
            if start > round_id:
                break
            current = probability
        return current


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
class RuntimeSettings:
    """Provider/runtime controls that do not alter the scientific state."""

    interaction_concurrency: int | None = None
    probe_concurrency: int | None = None
    max_physical_attempts: int | None = None
    max_cost_usd: float | None = None
    max_attempts_per_logical_completion: int | None = None
    retry_base_s: float = 1.0
    retry_max_s: float = 30.0
    retry_jitter_s: float = 0.25
    connect_timeout_s: float = 10.0
    read_timeout_s: float = 600.0
    request_timeout_s: float = 660.0
    pool_timeout_s: float = 10.0
    api_base_url: str = "https://api.deepseek.com"
    credential_source: str = "keychain"
    credential_service: str = "emergence-specialization.deepseek"
    credential_account: str = "api"
    user_id: str = "emergence-specialization"
    client_max_connections: int | None = None
    client_max_keepalive_connections: int | None = None

    def __post_init__(self) -> None:
        for name in ("interaction_concurrency", "probe_concurrency", "max_physical_attempts", "max_attempts_per_logical_completion"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or value < 1):
                raise ValueError(f"{name} must be positive or null")
        for name in ("max_cost_usd",):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative or null")
        for name in ("retry_base_s", "retry_max_s", "retry_jitter_s", "connect_timeout_s", "read_timeout_s", "request_timeout_s", "pool_timeout_s"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.retry_max_s < self.retry_base_s:
            raise ValueError("retry_max_s must be at least retry_base_s")
        if self.request_timeout_s < self.read_timeout_s:
            raise ValueError("request_timeout_s must be at least read_timeout_s")
        if self.credential_source not in {"keychain", "env"}:
            raise ValueError("credential_source must be keychain or env")
        if not self.api_base_url.startswith("https://"):
            raise ValueError("api_base_url must use https")
        if not self.user_id or not all(character.isalnum() or character in "-_" for character in self.user_id):
            raise ValueError("user_id must contain only letters, numbers, '-' or '_'")


@dataclass(frozen=True)
class InitialConditionSettings:
    """Optional explicit memory perturbations for sensitivity experiments."""

    experiences: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        required = {"world", "x", "y", "prediction", "confidence", "correct_answer", "was_correct"}
        for item in self.experiences:
            if not isinstance(item, dict):
                raise ValueError("initial condition experiences must be mappings")
            if "agent" not in item:
                raise ValueError("initial condition experience requires an agent")
            missing = required - set(item)
            if missing:
                raise ValueError(f"initial condition experience is missing: {sorted(missing)}")


@dataclass(frozen=True)
class RunConfig:
    protocol_version: str = "legacy"
    experiment: ExperimentSettings = field(default_factory=ExperimentSettings)
    environment: EnvironmentSettings = field(default_factory=EnvironmentSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    router: RouterSettings = field(default_factory=RouterSettings)
    condition: ConditionSettings = field(default_factory=ConditionSettings)
    feedback: FeedbackSettings | None = None
    initial_conditions: InitialConditionSettings = field(default_factory=InitialConditionSettings)
    interventions: tuple[dict[str, Any], ...] = ()
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    cost: CostSettings = field(default_factory=CostSettings)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    source_path: str | None = None
    source_hash: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.protocol_version, str) or not self.protocol_version.strip():
            raise ValueError("protocol_version must be a non-empty string")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def effective_feedback(self) -> FeedbackSettings:
        return self.feedback or FeedbackSettings.from_legacy(self.condition.memory_mode)

    @property
    def effective_interaction_concurrency(self) -> int:
        return self.runtime.interaction_concurrency or self.experiment.max_concurrency

    @property
    def effective_probe_concurrency(self) -> int:
        return self.runtime.probe_concurrency or self.experiment.max_concurrency

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
            experiment = replace(experiment, seed=seed, task_seed=None, router_seed=None, feedback_seed=None)
        agent = replace(self.agent, backend=backend) if backend is not None else self.agent
        logging = replace(self.logging, output_dir=output_dir) if output_dir is not None else self.logging
        return replace(self, experiment=experiment, agent=agent, logging=logging)


def _mapping(value: Any, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{section} must be a YAML mapping")
    return dict(value)


def normalize_checkpoints(raw: Any, num_rounds: int) -> tuple[int, ...]:
    """Normalize an explicit list or ``{every: N}`` schedule.

    Explicit ``[]`` remains empty, which is useful for interaction-only smoke
    tests. Regular schedules include the start and final checkpoint.
    """
    if raw is None:
        return ()
    if isinstance(raw, Mapping):
        unknown = set(raw) - {"every"}
        if unknown:
            raise ValueError(f"checkpoint schedule has unknown keys: {sorted(unknown)}")
        every = raw.get("every")
        if isinstance(every, bool) or not isinstance(every, int) or every <= 0:
            raise ValueError("checkpoint schedule 'every' must be a positive integer")
        values = list(range(0, num_rounds + 1, every))
        if num_rounds not in values:
            values.append(num_rounds)
        return tuple(sorted(set(values)))
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
        raise ValueError("checkpoints must be a list or a mapping with 'every'")
    values: list[int] = []
    for checkpoint in raw:
        if isinstance(checkpoint, bool) or not isinstance(checkpoint, int):
            raise ValueError("checkpoints must contain integers")
        values.append(checkpoint)
    if len(values) != len(set(values)):
        raise ValueError("checkpoints must not contain duplicates")
    return tuple(values)


def config_from_mapping(
    raw: Mapping[str, Any], *, source_path: str | None = None, source_hash: str | None = None
) -> RunConfig:
    raw = _mapping(dict(raw), "root")

    experiment = _mapping(raw.get("experiment"), "experiment")
    environment = _mapping(raw.get("environment"), "environment")
    agent = _mapping(raw.get("agent"), "agent")
    router = _mapping(raw.get("router"), "router")
    condition = _mapping(raw.get("condition"), "condition")
    feedback = _mapping(raw.get("feedback"), "feedback")
    initial_conditions = _mapping(raw.get("initial_conditions"), "initial_conditions")
    interventions_raw = raw.get("interventions", [])
    logging = _mapping(raw.get("logging"), "logging")
    cost = _mapping(raw.get("cost"), "cost")
    runtime = _mapping(raw.get("runtime"), "runtime")
    protocol_version = raw.get("protocol_version", "legacy")

    if "checkpoints" in experiment:
        experiment["checkpoints"] = normalize_checkpoints(
            experiment["checkpoints"], int(experiment.get("num_rounds", 80))
        )
    if "worlds" in environment:
        environment["worlds"] = tuple(environment["worlds"])
    if "schedule" in feedback:
        if not isinstance(feedback["schedule"], list):
            raise ValueError("feedback.schedule must be a list of [round, probability] pairs")
        feedback["schedule"] = tuple((int(item[0]), float(item[1])) for item in feedback["schedule"])
    if "experiences" in initial_conditions:
        if not isinstance(initial_conditions["experiences"], list):
            raise ValueError("initial_conditions.experiences must be a list")
        initial_conditions["experiences"] = tuple(dict(item) for item in initial_conditions["experiences"])
    if interventions_raw is None:
        interventions_raw = []
    if not isinstance(interventions_raw, list) or any(not isinstance(item, dict) for item in interventions_raw):
        raise ValueError("interventions must be a list of mappings")

    return RunConfig(
        protocol_version=str(protocol_version),
        experiment=ExperimentSettings(**experiment),
        environment=EnvironmentSettings(**environment),
        agent=AgentSettings(**agent),
        router=RouterSettings(**router),
        condition=ConditionSettings(**condition),
        feedback=FeedbackSettings(**feedback) if feedback else None,
        initial_conditions=InitialConditionSettings(**initial_conditions),
        interventions=tuple(dict(item) for item in interventions_raw),
        logging=LoggingSettings(**logging),
        cost=CostSettings(**cost),
        runtime=RuntimeSettings(**runtime),
        source_path=source_path,
        source_hash=source_hash,
    )


def load_config(path: str | Path) -> RunConfig:
    config_path = Path(path)
    raw_text = config_path.read_text(encoding="utf-8")
    raw = yaml.safe_load(raw_text)
    import hashlib

    return config_from_mapping(
        _mapping(raw, "root"),
        source_path=str(config_path),
        source_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
    )

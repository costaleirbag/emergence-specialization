"""End-to-end controlled experiment loop and command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import signal
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .agents import ExperimentalAgent, assert_initial_symmetry, stable_hash
from .config import RunConfig, config_from_mapping, load_config
from .credentials import CredentialStore
from .costs import estimate_usage_cost, summarize_usage
from .environment import HiddenWorldEnvironment
from .interventions import InterventionSpec, apply_memory_intervention
from .logging import RunLogger
from .memory import MemoryPolicy
from .metrics.behavioral import competence_matrix
from .metrics.complementarity import complementarity_metrics
from .metrics.hse import hierarchic_social_entropy
from .metrics.information import (
    mutual_information,
    normalized_mutual_information,
    normalized_utilization_entropy,
    utilization_entropy,
)
from .journal import ExecutionJournal
from .models import AgentResponse, Experience, InferenceRecord, ProbeObservation, Task
from .parsing import ResponseParseError, parse_agent_output
from .probes import load_probe_set
from .providers import DeepSeekDirectBackend, LLMBackend, MockBackend, OMPBackend
from .retry import retry_delay
from .router import ConfidenceRouter, RandomRouter, RouterDecision


@dataclass(frozen=True)
class SolveResult:
    agent_id: str
    response: AgentResponse | None
    records: tuple[InferenceRecord, ...]
    memory_inserted: tuple[dict[str, object], ...]
    error: str | None = None


class BudgetExceeded(RuntimeError):
    """A hard physical-attempt or cost guard stopped the run."""


class IncompleteLogicalWork(RuntimeError):
    """A round/checkpoint lacks one or more logical completions."""


class _ConsoleProgress:
    """Small dependency-free progress display for long concurrent batches."""

    def __init__(self, label: str, total: int, *, enabled: bool) -> None:
        self.label = label
        self.total = total
        self.enabled = enabled
        self.completed = 0
        self.started = time.perf_counter()

    def start(self) -> None:
        if self.enabled:
            self._render()

    def advance(self) -> None:
        self.completed += 1
        if self.enabled:
            self._render()

    def finish(self) -> None:
        if self.enabled:
            self.completed = self.total
            self._render()
            print(flush=True)

    def _render(self) -> None:
        elapsed = time.perf_counter() - self.started
        print(
            f"\r{self.label}: {self.completed}/{self.total} completions "
            f"({elapsed:.1f}s)",
            end="",
            flush=True,
        )


def make_backend(config: RunConfig) -> LLMBackend:
    if config.agent.backend == "mock":
        return MockBackend()
    if config.agent.backend == "omp":
        return OMPBackend(
            executable=config.agent.omp_executable,
            timeout_s=config.agent.omp_timeout_s,
            thinking=config.agent.thinking,
            working_directory=config.agent.omp_working_directory,
        )
    if config.agent.backend == "deepseek_direct":
        api_key = CredentialStore(
            config.runtime.credential_service,
            config.runtime.credential_account,
        ).get(source=config.runtime.credential_source)
        return DeepSeekDirectBackend(
            api_key=api_key,
            base_url=config.runtime.api_base_url,
            thinking=config.agent.thinking,
            max_tokens=config.agent.max_tokens or 128,
            connect_timeout_s=config.runtime.connect_timeout_s,
            read_timeout_s=config.runtime.read_timeout_s,
            request_timeout_s=config.runtime.request_timeout_s,
            pool_timeout_s=config.runtime.pool_timeout_s,
            user_id=config.runtime.user_id,
            max_connections=config.runtime.client_max_connections,
            max_keepalive_connections=config.runtime.client_max_keepalive_connections,
            credential_source=config.runtime.credential_source,
        )
    raise ValueError(f"Unknown backend {config.agent.backend!r}; use 'mock', 'omp', or 'deepseek_direct'")


class ExperimentRunner:
    """Owns all experimental state; providers are stateless inference adapters."""

    def __init__(self, config: RunConfig, backend: LLMBackend | None = None, *, resume_dir: str | Path | None = None) -> None:
        self.config = config
        self.backend = backend if backend is not None else make_backend(config)
        self.environment = HiddenWorldEnvironment(
            worlds=config.environment.worlds,
            x_min=config.environment.x_min,
            x_max=config.environment.x_max,
        )
        self.memory_policy = MemoryPolicy(config.agent.memory_strategy, config.agent.memory_k)
        self.router = (
            RandomRouter()
            if config.router.strategy == "random"
            else ConfidenceRouter(config.router.epsilon)
        )
        self.agents = [ExperimentalAgent(f"agent_{index}") for index in range(config.experiment.num_agents)]
        self._apply_initial_conditions()
        assert_initial_symmetry(
            self.agents,
            config.agent.system_prompt,
            require_empty_memory=not bool(config.initial_conditions.experiences),
        )
        self.agent_by_id = {agent.agent_id: agent for agent in self.agents}
        self.task_rng = random.Random(
            config.experiment.task_seed if config.experiment.task_seed is not None else config.experiment.seed
        )
        self.router_rng = random.Random(
            config.experiment.router_seed
            if config.experiment.router_seed is not None
            else config.experiment.seed + 1
        )
        self.feedback_rng = random.Random(
            config.experiment.feedback_seed
            if config.experiment.feedback_seed is not None
            else config.experiment.seed + 2
        )
        self.semaphore = asyncio.Semaphore(config.effective_interaction_concurrency)
        self.probe_semaphore = asyncio.Semaphore(config.effective_probe_concurrency)
        self.route_history: list[dict[str, Any]] = []
        self.token_usages: list[dict[str, Any] | None] = []
        self.previous_probe_routing: list[str | None] | None = None
        self.last_metrics: dict[str, Any] | None = None
        self.intervention_specs = [InterventionSpec.from_mapping(item) for item in config.interventions]
        self.resume_dir = Path(resume_dir).resolve() if resume_dir is not None else None
        self.journal: ExecutionJournal | None = None
        self.run_id: str | None = self.resume_dir.name if self.resume_dir else None
        self._cached_completions: dict[str, dict[str, Any]] = {}
        self._completed_rounds: set[int] = set()
        self._completed_checkpoints: set[int] = set()
        self._observed_cost_usd = 0.0
        self._physical_attempts = 0
        self._reserved_attempts = 0
        self._budget_lock = asyncio.Lock()

    def _apply_initial_conditions(self) -> None:
        for item in self.config.initial_conditions.experiences:
            agent_id = str(item["agent"])
            agent = next((candidate for candidate in self.agents if candidate.agent_id == agent_id), None)
            if agent is None:
                raise ValueError(f"initial condition references unknown agent: {agent_id}")
            values = {key: item[key] for key in ("round_id", "world", "x", "y", "prediction", "confidence", "correct_answer", "was_correct") if key in item}
            values.setdefault("round_id", 0)
            agent.observe(Experience(**values))

    def _apply_scheduled_interventions(self, round_id: int, logger: RunLogger) -> None:
        for spec in self.intervention_specs:
            if spec.trigger_round != round_id:
                continue
            if spec.operation.startswith("memory_"):
                payload = apply_memory_intervention(self.agents, spec)
                logger.event("intervention", payload)
            else:
                raise RuntimeError(
                    "population interventions are not wired into the fixed-N ExperimentRunner; "
                    "use PopulationState explicitly"
                )

    def _logical_id(
        self,
        *,
        phase: str,
        round_id: int | None,
        checkpoint: int | None,
        probe_index: int | None,
        agent_id: str,
        task: Task,
        inserted: Sequence[dict[str, object]],
        prompt_hash: str,
    ) -> str:
        payload = {
            "run_id": self.run_id,
            "config_hash": self.config.source_hash,
            "condition": self.config.condition.memory_mode,
            "seed": self.config.experiment.seed,
            "phase": phase,
            "round_id": round_id,
            "checkpoint": checkpoint,
            "probe_index": probe_index,
            "agent_id": agent_id,
            "task": task.experimenter_dict(),
            "memory_hash": stable_hash(json.dumps(inserted, sort_keys=True, separators=(",", ":"))),
            "prompt_hash": prompt_hash,
        }
        return stable_hash(json.dumps(payload, sort_keys=True, separators=(",", ":")))

    def _budget_guard(self) -> None:
        runtime = self.config.runtime
        attempts = self.journal.physical_attempts() if self.journal is not None else self._physical_attempts
        if runtime.max_physical_attempts is not None and attempts >= runtime.max_physical_attempts:
            raise BudgetExceeded(
                f"physical attempt budget exhausted: {attempts}/{runtime.max_physical_attempts}"
            )
        if runtime.max_cost_usd is not None and self._observed_cost_usd >= runtime.max_cost_usd:
            raise BudgetExceeded(
                f"cost budget exhausted: observed ${self._observed_cost_usd:.8f} / ${runtime.max_cost_usd:.8f}"
            )

    async def _reserve_attempt(self) -> None:
        """Reserve a physical-attempt slot before concurrent work starts.

        A semaphore limits throughput, but it does not make a budget check
        atomic.  Reservations prevent a burst of probe workers from crossing
        the hard physical-attempt ceiling together.
        """
        async with self._budget_lock:
            self._budget_guard()
            ceiling = self.config.runtime.max_physical_attempts
            if ceiling is not None and self._physical_attempts + self._reserved_attempts >= ceiling:
                raise BudgetExceeded(
                    f"physical attempt budget exhausted: {self._physical_attempts + self._reserved_attempts}/{ceiling}"
                )
            self._reserved_attempts += 1

    async def _release_attempt(self) -> None:
        async with self._budget_lock:
            self._reserved_attempts = max(0, self._reserved_attempts - 1)

    def _restore_existing_state(self, logger: RunLogger) -> None:
        """Rebuild scientific state from committed JSONL rounds before resume."""
        events_path = logger.events_path
        if not events_path.exists():
            return
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        round_events = sorted(
            (event for event in events if event.get("event") == "round_complete"),
            key=lambda event: int(event["round"]),
        )
        for event in round_events:
            round_id = int(event["round"])
            sampled = self.environment.sample_task(self.task_rng, task_id=f"round-{round_id}")
            logged_task = Task(**event["task"])
            if sampled.experimenter_dict() != logged_task.experimenter_dict():
                raise ValueError(f"Resume task sequence mismatch at round {round_id}")
            candidates = event.get("candidates", {})
            valid = [
                AgentResponse(agent_id, int(candidate["answer"]), float(candidate["confidence"]))
                for agent_id, candidate in sorted(candidates.items())
                if candidate.get("answer") is not None and candidate.get("confidence") is not None
            ]
            decision = self.router.select(valid, self.router_rng)
            if decision.selected_agent_id != event.get("selected_agent_id"):
                raise ValueError(f"Resume router state mismatch at round {round_id}")
            selected = next(response for response in valid if response.agent_id == decision.selected_agent_id)
            experience = Experience(
                round_id=round_id,
                world=logged_task.world,
                x=logged_task.x,
                y=logged_task.y,
                prediction=selected.answer,
                confidence=selected.confidence,
                correct_answer=logged_task.correct_answer,
                was_correct=self.environment.evaluate(logged_task, selected.answer),
            )
            recipients = [str(value) for value in event.get("feedback_recipients", [])]
            for recipient in recipients:
                if recipient not in self.agent_by_id:
                    raise ValueError(f"Resume references unknown feedback recipient {recipient}")
                self.agent_by_id[recipient].observe(experience)
            self.route_history.append({"world": logged_task.world, "selected_agent_id": selected.agent_id})
            self._completed_rounds.add(round_id)
        metric_events = sorted(
            (event for event in events if event.get("event") == "checkpoint_complete"),
            key=lambda event: int(event["checkpoint"]),
        )
        self._completed_checkpoints = {int(event["checkpoint"]) for event in metric_events}
        metric_path = logger.metrics_path
        if metric_path.exists():
            metrics = [json.loads(line) for line in metric_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if metrics:
                self.last_metrics = sorted(metrics, key=lambda row: int(row["checkpoint"]))[-1]
                self.previous_probe_routing = sorted(metrics, key=lambda row: int(row["checkpoint"]))[-1].get("probe_routing")
        if self.journal is not None:
            for payload in self.journal.attempt_payloads():
                self._physical_attempts += 1
                self._observed_cost_usd += float(payload.get("observed_cost_usd") or 0.0)
                self.token_usages.append(payload.get("token_usage"))

    def _open_journal(self, logger: RunLogger) -> None:
        self.journal = ExecutionJournal(logger.run_dir / "run_state.sqlite3")
        self.journal.set_state("run_id", logger.run_id)
        self.journal.set_state("config_hash", self.config.source_hash)
        self.journal.set_state("probe_set_path", self.config.logging.probe_set_path)
        self.journal.set_state("model", self.config.agent.model)
        self.journal.set_state("condition", self.config.condition.memory_mode)
        self.run_id = logger.run_id
        if self.resume_dir is not None:
            if self.journal.physical_attempts() == 0 and logger.events_path.exists():
                for event in (
                    json.loads(line)
                    for line in logger.events_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ):
                    if event.get("event") != "inference" or not event.get("logical_id"):
                        continue
                    logical_id = str(event["logical_id"])
                    attempt = int(event.get("attempt", 0))
                    self.journal.record_attempt(logical_id, attempt, event)
                    if event.get("error") is None and event.get("parsed_answer") is not None:
                        response = AgentResponse(
                            str(event["agent_id"]), int(event["parsed_answer"]), float(event["confidence"])
                        )
                        self.journal.record_logical_completion(
                            logical_id, {"record": event, "response": asdict(response), "error": None}
                        )
            self._restore_existing_state(logger)

    def _checkpoint_completed(self, checkpoint: int) -> bool:
        return checkpoint in self._completed_checkpoints

    @property
    def agent_ids(self) -> list[str]:
        return [agent.agent_id for agent in self.agents]

    @property
    def model_parameters(self) -> dict[str, Any]:
        return {
            "thinking": self.config.agent.thinking,
            "temperature": self.config.agent.temperature,
            "top_p": self.config.agent.top_p,
            "max_tokens": self.config.agent.max_tokens or (128 if self.config.agent.backend == "deepseek_direct" else None),
            "note": (
                "temperature/top_p/max_tokens are experimental metadata only for the OMP backend; "
                "OMP 17.2.10 does not document controls for them."
                if self.config.agent.backend == "omp"
                else "DeepSeek Direct uses documented JSON Output, max_tokens, and thinking=disabled."
                if self.config.agent.backend == "deepseek_direct"
                else "mock backend ignores decoding parameters"
            ),
            "direct_request": {
                "response_format": {"type": "json_object"},
                "stream": False,
                "thinking": "disabled",
            }
            if self.config.agent.backend == "deepseek_direct"
            else None,
        }

    @property
    def actual_model_label(self) -> str:
        return self.config.agent.model if self.config.agent.backend in {"omp", "deepseek_direct"} else "mock/deterministic-modular-learner"

    async def _solve(
        self,
        *,
        agent: ExperimentalAgent,
        task: Task,
        phase: str,
        round_id: int | None,
        checkpoint: int | None,
        probe_index: int | None,
        memory_snapshot: Sequence[Experience] | None = None,
    ) -> SolveResult:
        user_prompt, inserted = agent.prompt_parts(task, self.memory_policy, memory_snapshot=memory_snapshot)
        system_prompt = self.config.agent.system_prompt
        prompt_hash = stable_hash(system_prompt + "\n\n" + user_prompt)
        system_prompt_hash = stable_hash(system_prompt)
        logical_id = self._logical_id(
            phase=phase,
            round_id=round_id,
            checkpoint=checkpoint,
            probe_index=probe_index,
            agent_id=agent.agent_id,
            task=task,
            inserted=inserted,
            prompt_hash=prompt_hash,
        )
        if self.journal is not None:
            cached = self.journal.completed(logical_id)
            if cached is not None:
                record = InferenceRecord(**cached["record"])
                response_payload = cached.get("response")
                response = AgentResponse(**response_payload) if response_payload else None
                return SolveResult(
                    agent_id=agent.agent_id,
                    response=response,
                    records=(),
                    memory_inserted=tuple(inserted),
                    error=cached.get("error"),
                )
        records: list[InferenceRecord] = []
        final_error: str | None = None
        max_attempts = self.config.runtime.max_attempts_per_logical_completion or (self.config.experiment.technical_retries + 1)

        for attempt in range(max_attempts):
            await self._reserve_attempt()
            semaphore = self.probe_semaphore if phase == "probe" else self.semaphore
            try:
                async with semaphore:
                    backend_response = await self.backend.complete(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=self.config.agent.model,
                        model_parameters=self.model_parameters,
                    )
            finally:
                await self._release_attempt()
            parsed_answer: int | None = None
            confidence: float | None = None
            answer_in_domain: bool | None = None
            semantic_violation: str | None = None
            error = backend_response.error
            if error is None:
                if backend_response.raw_response is None:
                    error = "backend returned neither response text nor error"
                else:
                    try:
                        parsed = parse_agent_output(backend_response.raw_response)
                        parsed_answer, confidence = parsed.answer, parsed.confidence
                        answer_in_domain = parsed.answer_in_domain
                        semantic_violation = parsed.semantic_violation
                    except ResponseParseError as exc:
                        error = f"ResponseParseError: {exc}"
                        error_category = "parse_error"
                        retryable = True
                    else:
                        error_category = None
                        retryable = True
                if backend_response.raw_response is None:
                    error_category = "empty_content"
                    retryable = True
            else:
                error_category = backend_response.error_category or "backend_error"
                retryable = backend_response.retryable
            observed_cost = estimate_usage_cost(
                backend_response.token_usage,
                input_per_million_tokens=self.config.cost.input_per_million_tokens,
                cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                output_per_million_tokens=self.config.cost.output_per_million_tokens,
            )
            record = InferenceRecord(
                phase=phase,
                round_id=round_id,
                checkpoint=checkpoint,
                probe_index=probe_index,
                agent_id=agent.agent_id,
                attempt=attempt,
                retry_count=attempt,
                model=self.actual_model_label,
                model_parameters=self.model_parameters,
                task=task.experimenter_dict(),
                memory_inserted=inserted,
                prompt_hash=prompt_hash,
                system_prompt_hash=system_prompt_hash,
                raw_model_response=backend_response.raw_response,
                parsed_answer=parsed_answer,
                confidence=confidence,
                latency_s=backend_response.latency_s,
                token_usage=backend_response.token_usage,
                error=error,
                logical_id=logical_id,
                error_category=error_category,
                retryable=retryable,
                http_status=backend_response.http_status,
                retry_after_s=backend_response.retry_after_s,
                provider_metadata=backend_response.provider_metadata,
                observed_cost_usd=observed_cost,
                answer_in_domain=answer_in_domain,
                semantic_violation=semantic_violation,
            )
            records.append(record)
            self._physical_attempts += 1
            if observed_cost is not None:
                self._observed_cost_usd += observed_cost
            if self.journal is not None:
                self.journal.record_attempt(logical_id, attempt, record)
            if error is None:
                response = AgentResponse(agent.agent_id, parsed_answer, confidence)
                if self.journal is not None:
                    self.journal.record_logical_completion(
                        logical_id,
                        {"record": asdict(record), "response": asdict(response), "error": None},
                    )
                return SolveResult(
                    agent_id=agent.agent_id,
                    response=response,
                    records=tuple(records),
                    memory_inserted=tuple(inserted),
                )
            final_error = error
            if error_category == "insufficient_balance":
                raise BudgetExceeded("DeepSeek API reported insufficient balance (HTTP 402); stopping immediately")
            if not retryable or attempt + 1 >= max_attempts:
                break
            delay = retry_delay(
                attempt,
                base_s=self.config.runtime.retry_base_s,
                max_s=self.config.runtime.retry_max_s,
                jitter_s=self.config.runtime.retry_jitter_s,
                logical_id=logical_id,
                retry_after_s=backend_response.retry_after_s,
            )
            if delay > 0:
                await asyncio.sleep(delay)

        return SolveResult(
            agent_id=agent.agent_id,
            response=None,
            records=tuple(records),
            memory_inserted=tuple(inserted),
            error=final_error,
        )

    def _log_inferences(self, logger: RunLogger, results: Iterable[SolveResult]) -> None:
        for result in results:
            for record in result.records:
                self.token_usages.append(record.token_usage)
                logger.event(
                    "inference",
                    {
                        "run_id": logger.run_id,
                        "seed": self.config.experiment.seed,
                        "condition": self.config.condition.memory_mode,
                        **asdict(record),
                    },
                )

    async def _evaluate_checkpoint(
        self,
        *,
        checkpoint: int,
        probes: Sequence[Task],
        probe_set_hash: str,
        logger: RunLogger,
        memory_snapshot: Mapping[str, Sequence[Experience]] | None = None,
    ) -> dict[str, Any]:
        """Evaluate frozen snapshots; this function never calls ``observe``."""
        current_memory = {agent.agent_id: tuple(agent.memory) for agent in self.agents}
        memory_before = (
            current_memory
            if memory_snapshot is None
            else {agent.agent_id: tuple(memory_snapshot.get(agent.agent_id, ())) for agent in self.agents}
        )
        snapshot_payload = {
            agent_id: [experience.prompt_dict() for experience in memory]
            for agent_id, memory in memory_before.items()
        }
        snapshot_hash = stable_hash(json.dumps(snapshot_payload, sort_keys=True, separators=(",", ":")))
        if self.journal is not None:
            previous_snapshot = self.journal.snapshot(checkpoint)
            if previous_snapshot is not None and previous_snapshot[0] != snapshot_hash:
                raise ValueError(f"Checkpoint {checkpoint} memory snapshot hash mismatch; refusing to resume")
            self.journal.record_snapshot(checkpoint, snapshot_hash, snapshot_payload)
        progress = _ConsoleProgress(
            f"CHECKPOINT {checkpoint}: probe evaluation",
            len(probes) * len(self.agents),
            enabled=self.config.experiment.console_summary,
        )
        progress.start()
        jobs = [
            self._solve(
                agent=agent,
                task=task,
                phase="probe",
                round_id=None,
                checkpoint=checkpoint,
                probe_index=probe_index,
                memory_snapshot=memory_before[agent.agent_id],
            )
            for probe_index, task in enumerate(probes)
            for agent in self.agents
        ]
        async def run_probe_job(index: int, job: Any) -> tuple[int, SolveResult]:
            result = await job
            progress.advance()
            return index, result

        try:
            indexed_results = await asyncio.gather(*(run_probe_job(index, job) for index, job in enumerate(jobs)))
        finally:
            progress.finish()
        flat_results = [result for _, result in sorted(indexed_results)]
        self._log_inferences(logger, flat_results)
        if any(tuple(agent.memory) != current_memory[agent.agent_id] for agent in self.agents):
            raise AssertionError("Probe evaluation mutated an agent memory")
        if any(result.response is None for result in flat_results):
            logger.event(
                "checkpoint_incomplete",
                {
                    "checkpoint": checkpoint,
                    "missing_agents": [result.agent_id for result in flat_results if result.response is None],
                },
            )
            raise IncompleteLogicalWork(f"Checkpoint {checkpoint} has missing logical probe completions")

        by_probe: list[list[SolveResult]] = [
            flat_results[index * len(self.agents) : (index + 1) * len(self.agents)]
            for index in range(len(probes))
        ]
        behavioral_matrix: list[list[int]] = [[] for _ in self.agents]
        observations: dict[str, list[ProbeObservation]] = {agent.agent_id: [] for agent in self.agents}
        probe_routing: list[str | None] = []
        for probe_index, (task, results) in enumerate(zip(probes, by_probe)):
            valid = [result.response for result in results if result.response is not None]
            if len(valid) != len(results):
                raise IncompleteLogicalWork(f"Checkpoint {checkpoint} has missing logical probe completions")
            probe_routing.append(self.router.probe_choice(valid, self.router_rng))
            for agent_index, result in enumerate(results):
                response = result.response
                success = int(response is not None and self.environment.evaluate(task, response.answer))
                behavioral_matrix[agent_index].append(success)
                observations[result.agent_id].append(
                    ProbeObservation(probe_index, task, response, error=result.error)
                )

        if checkpoint == 0:
            prompt_hashes_by_probe: dict[str, str] = {}
            for probe_index, results in enumerate(by_probe):
                hashes = {result.records[0].prompt_hash for result in results}
                if len(hashes) != 1:
                    raise AssertionError("Initial prompt bytes must be identical across agents")
                prompt_hashes_by_probe[str(probe_index)] = hashes.pop()
            logger.event(
                "initial_symmetry_verified",
                {
                    "checkpoint": 0,
                    "system_prompt_hash": stable_hash(self.config.agent.system_prompt),
                    "prompt_hashes_by_probe": prompt_hashes_by_probe,
                },
            )

        selected_worlds = [item["world"] for item in self.route_history]
        selected_agents = [item["selected_agent_id"] for item in self.route_history]
        routing_counts = {
            world: {agent_id: 0 for agent_id in self.agent_ids} for world in self.config.environment.worlds
        }
        for world, agent_id in zip(selected_worlds, selected_agents):
            routing_counts[world][agent_id] += 1
        hse = hierarchic_social_entropy(behavioral_matrix)
        complementarity = complementarity_metrics(behavioral_matrix)
        temporal_stability: float | None = None
        if self.previous_probe_routing is not None:
            comparable = [
                (before, after)
                for before, after in zip(self.previous_probe_routing, probe_routing)
                if before is not None and after is not None
            ]
            temporal_stability = (
                sum(before == after for before, after in comparable) / len(comparable) if comparable else None
            )
        self.previous_probe_routing = probe_routing

        payload: dict[str, Any] = {
            "run_id": logger.run_id,
            "checkpoint": checkpoint,
            "probe_set_hash": probe_set_hash,
            "probe_count": len(probes),
            "behavioral_matrix": behavioral_matrix,
            "agent_ids": self.agent_ids,
            "individual_accuracy": complementarity["individual_accuracy"],
            "competence_matrix": competence_matrix(behavioral_matrix, probes, self.agent_ids),
            "best_individual_accuracy": complementarity["best_individual_accuracy"],
            "oracle_society_accuracy": complementarity["oracle_society_accuracy"],
            "oracle_gain": complementarity["oracle_gain"],
            "pairwise_behavioral_cosine_distance": hse["distance_matrix"],
            "hse": hse["hse"],
            "normalized_hse": hse["normalized_hse"],
            "hse_merge_heights": hse["merge_heights"],
            "hse_intervals": hse.get("intervals", []),
            "routing_counts_by_world_agent": routing_counts,
            "task_agent_mutual_information": mutual_information(selected_worlds, selected_agents),
            "normalized_task_agent_mutual_information": normalized_mutual_information(
                selected_worlds, selected_agents
            ),
            "utilization_entropy": utilization_entropy(selected_agents),
            "normalized_utilization_entropy": normalized_utilization_entropy(
                selected_agents, len(self.agents)
            ),
            "probe_routing": probe_routing,
            "temporal_role_stability": temporal_stability,
        }
        logger.metrics(payload)
        logger.event(
            "checkpoint_complete",
            {
                "checkpoint": checkpoint,
                "probe_set_hash": probe_set_hash,
                "memory_snapshot_hash": snapshot_hash,
                "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
            },
        )
        self._completed_checkpoints.add(checkpoint)
        self.last_metrics = payload
        return payload

    def _distribute_feedback(self, selected: AgentResponse, task: Task, round_id: int) -> tuple[Experience, list[str]]:
        experience = Experience(
            round_id=round_id,
            world=task.world,
            x=task.x,
            y=task.y,
            prediction=selected.answer,
            confidence=selected.confidence,
            correct_answer=task.correct_answer,
            was_correct=self.environment.evaluate(task, selected.answer),
        )
        policy = self.config.effective_feedback
        mode = policy.mode
        if mode == "probabilistic" or policy.schedule:
            mode = "private" if self.feedback_rng.random() < policy.probability_at(round_id) else "shared"
        if mode == "private":
            recipient = self.agent_by_id[selected.agent_id]
            recipient.observe(experience)
            return experience, [recipient.agent_id]
        if mode == "shared":
            for agent in self.agents:
                agent.observe(experience)
            if any(agent.memory != self.agents[0].memory for agent in self.agents[1:]):
                raise AssertionError("Shared feedback must keep all memories equal")
            return experience, self.agent_ids
        if mode == "none":
            return experience, []
        raise AssertionError(f"Unexpected memory mode {mode!r}")

    def _print_round(
        self,
        round_id: int,
        task: Task,
        results: Sequence[SolveResult],
        memory_counts_before: dict[str, int],
        selected: AgentResponse,
        recipients: Sequence[str],
    ) -> None:
        print(f"\nROUND {round_id} — {task.world}")
        print("              answer    confidence    relevant experiences")
        for result in results:
            response = result.response
            answer = str(response.answer) if response is not None else "ERROR"
            confidence = f"{response.confidence:.2f}" if response is not None else "--"
            marker = "  <-- selected" if result.agent_id == selected.agent_id else ""
            print(f"{result.agent_id:>11} {answer:>8} {confidence:>13} {memory_counts_before[result.agent_id]:>22}{marker}")
        print(f"correct: {task.correct_answer}")
        print(f"feedback recipients: {', '.join(recipients) if recipients else 'none'}")

    async def run(self) -> Path:
        probes, probe_set_hash = load_probe_set(self.config.logging.probe_set_path)
        if self.resume_dir is not None:
            run_id = self.resume_dir.name
            logger = RunLogger(self.resume_dir.parent, run_id, resume=True)
            self._open_journal(logger)
            existing_metadata = json.loads((logger.run_dir / "metadata.json").read_text(encoding="utf-8"))
            if existing_metadata.get("probe_set_hash") != probe_set_hash:
                raise ValueError("Resume probe-set hash mismatch; refusing to continue")
        else:
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            run_id = (
                f"{self.config.condition.memory_mode}-seed{self.config.experiment.seed}-{timestamp}-{uuid.uuid4().hex[:8]}"
            )
            logger = RunLogger(self.config.logging.output_dir, run_id)
            self._open_journal(logger)
            logger.write_metadata(
                {
                "config": self.config.as_dict(),
                "probe_set_hash": probe_set_hash,
                "effective_rng_seeds": {
                    "experiment": self.config.experiment.seed,
                    "task": (
                        self.config.experiment.task_seed
                        if self.config.experiment.task_seed is not None
                        else self.config.experiment.seed
                    ),
                    "router_tie_breaking": (
                        self.config.experiment.router_seed
                        if self.config.experiment.router_seed is not None
                        else self.config.experiment.seed + 1
                    ),
                    "feedback_locality": (
                        self.config.experiment.feedback_seed
                        if self.config.experiment.feedback_seed is not None
                        else self.config.experiment.seed + 2
                    ),
                    "probe_generation": "recorded in data/probe_set.json",
                },
                "backend": self.backend.metadata(),
                "execution_policy": {
                    "interaction_concurrency": self.config.effective_interaction_concurrency,
                    "probe_concurrency": self.config.effective_probe_concurrency,
                    "max_attempts_per_logical_completion": (
                        self.config.runtime.max_attempts_per_logical_completion
                        or self.config.experiment.technical_retries + 1
                    ),
                    "max_physical_attempts": self.config.runtime.max_physical_attempts,
                    "max_cost_usd": self.config.runtime.max_cost_usd,
                    "retry_base_s": self.config.runtime.retry_base_s,
                    "retry_max_s": self.config.runtime.retry_max_s,
                    "retry_jitter_s": self.config.runtime.retry_jitter_s,
                },
                "scientific_controls": {
                    "agent_ids_are_host_side_only": True,
                    "same_system_prompt": True,
                    "empty_initial_memory": not bool(self.config.initial_conditions.experiences),
                    "initial_condition_count": len(self.config.initial_conditions.experiences),
                    "provider_session_independent": self.config.agent.backend in {"omp", "deepseek_direct"},
                    "probe_updates_memory": False,
                    "hidden_rules_in_model_prompt": False,
                    "feedback_policy": self.config.effective_feedback.as_label(),
                },
                }
            )
            logger.event(
                "run_started",
                {
                    "run_id": run_id,
                    "seed": self.config.experiment.seed,
                    "condition": self.config.condition.memory_mode,
                    "num_agents": len(self.agents),
                    "num_rounds": self.config.experiment.num_rounds,
                },
            )
            if self.config.initial_conditions.experiences:
                logger.event(
                    "initial_condition",
                    {
                        "experiences": [
                            {"agent": agent.agent_id, **experience.prompt_dict()}
                            for agent in self.agents
                            for experience in agent.memory
                        ]
                    },
                )
        self.run_id = run_id
        try:
            if self.config.experiment.console_summary:
                nominal_interactions = self.config.experiment.num_rounds * len(self.agents)
                nominal_probes = len(self.config.experiment.checkpoints) * len(probes) * len(self.agents)
                nominal_total = nominal_interactions + nominal_probes
                max_total = nominal_total * (self.config.experiment.technical_retries + 1)
                if self.config.runtime.max_physical_attempts is not None:
                    max_total = min(max_total, self.config.runtime.max_physical_attempts)
                print("\nEXPERIMENT PLAN")
                print(f"model: {self.config.agent.model} | condition: {self.config.condition.memory_mode}")
                print(
                    f"nominal completions: {nominal_total} "
                    f"({nominal_interactions} interaction + {nominal_probes} probe)"
                )
                print(
                    f"retry ceiling: {max_total} physical completions "
                    f"(technical_retries={self.config.experiment.technical_retries})"
                )
            if 0 in self.config.experiment.checkpoints and not self._checkpoint_completed(0):
                await self._evaluate_checkpoint(
                    checkpoint=0, probes=probes, probe_set_hash=probe_set_hash, logger=logger
                )
            # A run can fail after completing the interaction round at a
            # checkpoint (for example, a transient probe outage).  On resume,
            # ``_completed_rounds`` already contains that round, so the normal
            # loop would skip it and never revisit the incomplete checkpoint.
            # Repair pending checkpoints before advancing to later rounds;
            # cached logical completions keep this bounded to missing work.
            pending_checkpoints = [
                checkpoint
                for checkpoint in self.config.experiment.checkpoints
                if checkpoint > 0
                and checkpoint in self._completed_rounds
                and not self._checkpoint_completed(checkpoint)
            ]
            for checkpoint in pending_checkpoints:
                snapshot = self.journal.snapshot(checkpoint) if self.journal is not None else None
                if snapshot is None:
                    raise ValueError(
                        f"Checkpoint {checkpoint} is incomplete but has no immutable memory snapshot; refusing to resume"
                    )
                _, snapshot_payload = snapshot
                checkpoint_memory = {
                    agent_id: tuple(Experience(**item) for item in values)
                    for agent_id, values in snapshot_payload.items()
                }
                await self._evaluate_checkpoint(
                    checkpoint=checkpoint,
                    probes=probes,
                    probe_set_hash=probe_set_hash,
                    logger=logger,
                    memory_snapshot=checkpoint_memory,
                )
            for round_id in range(1, self.config.experiment.num_rounds + 1):
                if round_id in self._completed_rounds:
                    continue
                self._apply_scheduled_interventions(round_id, logger)
                task = self.environment.sample_task(self.task_rng, task_id=f"round-{round_id}")
                memory_counts_before = {agent.agent_id: len(agent.memory) for agent in self.agents}
                if self.config.experiment.console_summary:
                    print(
                        f"\nROUND {round_id}/{self.config.experiment.num_rounds} — "
                        f"running {len(self.agents)} interaction completions...",
                        flush=True,
                    )
                results = list(
                    await asyncio.gather(
                        *(
                            self._solve(
                                agent=agent,
                                task=task,
                                phase="round",
                                round_id=round_id,
                                checkpoint=None,
                                probe_index=None,
                            )
                            for agent in self.agents
                        )
                    )
                )
                self._log_inferences(logger, results)
                valid = [result.response for result in results if result.response is not None]
                if len(valid) != len(results):
                    logger.event(
                        "round_incomplete",
                        {
                            "round": round_id,
                            "task": task.experimenter_dict(),
                            "candidate_errors": {result.agent_id: result.error for result in results},
                        },
                    )
                    raise IncompleteLogicalWork(f"Round {round_id} has missing logical completions")
                decision: RouterDecision = self.router.select(valid, self.router_rng)
                selected = next(response for response in valid if response.agent_id == decision.selected_agent_id)
                experience, recipients = self._distribute_feedback(selected, task, round_id)
                candidate_payload = {
                    result.agent_id: {
                        "answer": result.response.answer if result.response else None,
                        "confidence": result.response.confidence if result.response else None,
                        "error": result.error,
                    }
                    for result in results
                }
                round_payload = {
                    "round": round_id,
                    "task": task.experimenter_dict(),
                    "correct_answer": task.correct_answer,
                    "candidates": candidate_payload,
                    "selected_agent_id": selected.agent_id,
                    "selected_answer": selected.answer,
                    "selected_correct": experience.was_correct,
                    "selection_mode": decision.selection_mode,
                    "tied_agent_ids": list(decision.tied_agent_ids),
                    "feedback_recipients": recipients,
                }
                logger.event("round_complete", round_payload)
                if self.journal is not None:
                    self.journal.record_round_commit(round_id, round_payload)
                self._completed_rounds.add(round_id)
                self.route_history.append({"world": task.world, "selected_agent_id": selected.agent_id})
                if self.config.experiment.console_summary:
                    self._print_round(round_id, task, results, memory_counts_before, selected, recipients)
                if round_id in self.config.experiment.checkpoints and not self._checkpoint_completed(round_id):
                    await self._evaluate_checkpoint(
                        checkpoint=round_id, probes=probes, probe_set_hash=probe_set_hash, logger=logger
                    )
                    self._completed_checkpoints.add(round_id)
            summary = {
                "run_id": run_id,
                "status": "completed",
                "condition": self.config.condition.memory_mode,
                "seed": self.config.experiment.seed,
                "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
                "routing_counts": dict(Counter(item["selected_agent_id"] for item in self.route_history)),
                "final_metrics": self.last_metrics,
                "physical_attempts": self._physical_attempts,
                "observed_cost_usd": self._observed_cost_usd if self._observed_cost_usd else None,
                "usage": summarize_usage(
                    self.token_usages,
                    currency=self.config.cost.currency,
                    input_per_million_tokens=self.config.cost.input_per_million_tokens,
                    cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                    output_per_million_tokens=self.config.cost.output_per_million_tokens,
                ),
            }
            logger.write_summary(summary)
            if self.journal is not None:
                self.journal.set_state("status", "completed")
                self.journal.close()
            close = getattr(self.backend, "close", None)
            if callable(close):
                result = close()
                if hasattr(result, "__await__"):
                    await result
            if self.config.experiment.console_summary:
                self._print_final_summary(summary)
            return logger.run_dir
        except KeyboardInterrupt:
            completed_logical = self.journal.completed_count() if self.journal else None
            logger.event("run_interrupted", {"completed_logical": completed_logical})
            logger.write_summary(
                {
                    "run_id": run_id,
                    "status": "interrupted",
                    "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
                    "physical_attempts": self._physical_attempts,
                    "observed_cost_usd": self._observed_cost_usd if self._observed_cost_usd else None,
                    "usage": summarize_usage(
                        self.token_usages,
                        currency=self.config.cost.currency,
                        input_per_million_tokens=self.config.cost.input_per_million_tokens,
                        cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                        output_per_million_tokens=self.config.cost.output_per_million_tokens,
                    ),
                }
            )
            if self.journal is not None:
                self.journal.set_state("status", "interrupted")
                self.journal.close()
            print(
                f"\nRUN INTERRUPTED: {logger.run_dir}\n"
                f"completed logical calls: {completed_logical if completed_logical is not None else 'unknown'}\n"
                f"observed cost: ${self._observed_cost_usd:.8f}\n"
                f"resume: uv run python -m emergent_specialization.experiment --resume {logger.run_dir} --confirm-real",
                flush=True,
            )
            raise
        except asyncio.CancelledError:
            completed_logical = self.journal.completed_count() if self.journal else None
            logger.event("run_interrupted", {"completed_logical": completed_logical})
            logger.write_summary(
                {
                    "run_id": run_id,
                    "status": "interrupted",
                    "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
                    "physical_attempts": self._physical_attempts,
                    "observed_cost_usd": self._observed_cost_usd if self._observed_cost_usd else None,
                    "usage": summarize_usage(
                        self.token_usages,
                        currency=self.config.cost.currency,
                        input_per_million_tokens=self.config.cost.input_per_million_tokens,
                        cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                        output_per_million_tokens=self.config.cost.output_per_million_tokens,
                    ),
                }
            )
            if self.journal is not None:
                self.journal.set_state("status", "interrupted")
                self.journal.close()
            print(
                f"\nRUN INTERRUPTED: {logger.run_dir}\n"
                f"completed logical calls: {completed_logical if completed_logical is not None else 'unknown'}\n"
                f"observed cost: ${self._observed_cost_usd:.8f}\n"
                f"resume: uv run python -m emergent_specialization.experiment --resume {logger.run_dir} --confirm-real",
                flush=True,
            )
            raise
        except Exception as exc:
            logger.event("run_failed", {"error": f"{type(exc).__name__}: {exc}"})
            logger.write_summary(
                {
                    "run_id": run_id,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
                    "physical_attempts": self._physical_attempts,
                    "observed_cost_usd": self._observed_cost_usd if self._observed_cost_usd else None,
                    "usage": summarize_usage(
                        self.token_usages,
                        currency=self.config.cost.currency,
                        input_per_million_tokens=self.config.cost.input_per_million_tokens,
                        cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                        output_per_million_tokens=self.config.cost.output_per_million_tokens,
                    ),
                }
            )
            if self.journal is not None:
                self.journal.set_state("status", "failed")
                self.journal.close()
            raise

    @staticmethod
    def _print_final_summary(summary: dict[str, Any]) -> None:
        metrics = summary.get("final_metrics") or {}
        print("\nFINAL SUMMARY")
        print(f"run: {summary['run_id']}")
        print(f"routing counts: {json.dumps(summary['routing_counts'], sort_keys=True)}")
        print(f"memory counts: {json.dumps(summary['memory_counts'], sort_keys=True)}")
        if summary.get("observed_cost_usd") is not None:
            print(f"observed cost estimate: ${summary['observed_cost_usd']:.8f}")
        usage = summary.get("usage") or {}
        if usage.get("status") == "provider_reported":
            print(f"provider-reported cost: {usage['reported_cost']:.8f} (OMP currency unit)")
        elif usage.get("status") == "estimated":
            print(f"estimated cost: {usage['estimated_cost']:.8f} {usage['currency']}")
        else:
            print(f"token usage/cost: {usage.get('status', 'unavailable')}")
        if metrics:
            print(f"normalized utilization entropy: {metrics['normalized_utilization_entropy']:.4f}")
            print(f"normalized task-agent MI: {metrics['normalized_task_agent_mutual_information']:.4f}")
            print(f"normalized HSE: {metrics['normalized_hse']:.4f}")
            print(f"oracle gain: {metrics['oracle_gain']:.4f}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the emergent-specialization experiment.")
    parser.add_argument("--config", help="YAML config path")
    parser.add_argument("--resume", help="Existing run directory to resume in place")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic MockBackend; no model calls")
    parser.add_argument("--confirm-real", action="store_true", help="Required acknowledgement for direct real inference")
    parser.add_argument("--num-rounds", type=int, help="Override number of interaction rounds")
    parser.add_argument("--seed", type=int, help="Override experiment/task/router seed")
    parser.add_argument("--output-dir", help="Override the parent directory for a run")
    parser.add_argument(
        "--report",
        action="store_true",
        help="After a completed run, execute the notebook and export an HTML report (requires the report group)",
    )
    parser.add_argument("--report-output", help="Override the generated report directory")
    return parser


async def async_main(argv: Iterable[str] | None = None) -> Path:
    args = build_argument_parser().parse_args(list(argv) if argv is not None else None)
    if bool(args.config) == bool(args.resume):
        raise SystemExit("exactly one of --config or --resume is required")
    if args.resume and any(value is not None for value in (args.num_rounds, args.seed, args.output_dir)):
        raise SystemExit("--resume cannot be combined with --num-rounds, --seed, or --output-dir")
    if args.resume:
        resume_dir = Path(args.resume).expanduser().resolve()
        metadata = json.loads((resume_dir / "metadata.json").read_text(encoding="utf-8"))
        raw_config = metadata.get("config")
        if not isinstance(raw_config, dict):
            raise SystemExit("resume metadata has no immutable config")
        config = config_from_mapping(
            raw_config,
            source_path=raw_config.get("source_path"),
            source_hash=raw_config.get("source_hash"),
        )
        if metadata.get("config", {}).get("source_hash") != config.source_hash:
            raise SystemExit("resume config hash is invalid")
        summary_path = resume_dir / "summary.json"
        from .health import run_health

        health = run_health(resume_dir)
        print(
            f"RESUME PLAN: expected={health['expected_logical_completions']} "
            f"complete={health['successful_logical_completions']} "
            f"missing={health['missing_logical_completions']} "
            f"physical_attempts={health['physical_attempts']} "
            f"observed_cost_usd={health.get('observed_cost_usd')}"
        )
        if summary_path.exists():
            if health["status"] == "completed" and health["missing_logical_completions"] == 0:
                print(f"Resume is already complete; 0 API calls: {resume_dir}")
                return resume_dir
        if config.agent.backend == "deepseek_direct" and not args.confirm_real:
            raise SystemExit("resuming direct real inference requires --confirm-real")
        runner = ExperimentRunner(config, resume_dir=resume_dir)
        run_dir = await runner.run()
    else:
        config = load_config(args.config).overridden(
            num_rounds=args.num_rounds,
            seed=args.seed,
            output_dir=args.output_dir,
            backend="mock" if args.dry_run else None,
        )
        if config.agent.backend == "deepseek_direct" and not args.dry_run and not args.confirm_real:
            raise SystemExit("direct real inference requires --confirm-real")
        run_dir = await ExperimentRunner(config).run()
    print(f"Raw events and metrics: {run_dir}")
    if args.report:
        from .reporting import generate_run_report

        report_dir = generate_run_report(run_dir, args.report_output)
        print(f"Executed notebook: {report_dir / 'report.ipynb'}")
        print(f"HTML report: {report_dir / 'report.html'}")
    return run_dir


def main(argv: Iterable[str] | None = None) -> None:
    def interrupt_handler(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    old_sigterm = signal.signal(signal.SIGTERM, interrupt_handler)
    try:
        asyncio.run(async_main(argv))
    finally:
        signal.signal(signal.SIGTERM, old_sigterm)


if __name__ == "__main__":
    main()

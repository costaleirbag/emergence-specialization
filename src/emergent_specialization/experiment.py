"""End-to-end controlled experiment loop and command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from .agents import ExperimentalAgent, assert_initial_symmetry, stable_hash
from .config import RunConfig, load_config
from .costs import summarize_usage
from .environment import HiddenWorldEnvironment
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
from .models import AgentResponse, Experience, InferenceRecord, ProbeObservation, Task
from .parsing import ResponseParseError, parse_agent_output
from .probes import load_probe_set
from .providers import LLMBackend, MockBackend, OMPBackend
from .router import ConfidenceRouter, RouterDecision


@dataclass(frozen=True)
class SolveResult:
    agent_id: str
    response: AgentResponse | None
    records: tuple[InferenceRecord, ...]
    memory_inserted: tuple[dict[str, object], ...]
    error: str | None = None


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
    raise ValueError(f"Unknown backend {config.agent.backend!r}; use 'mock' or 'omp'")


class ExperimentRunner:
    """Owns all experimental state; providers are stateless inference adapters."""

    def __init__(self, config: RunConfig, backend: LLMBackend | None = None) -> None:
        self.config = config
        self.backend = backend if backend is not None else make_backend(config)
        self.environment = HiddenWorldEnvironment(
            worlds=config.environment.worlds,
            x_min=config.environment.x_min,
            x_max=config.environment.x_max,
        )
        self.memory_policy = MemoryPolicy(config.agent.memory_strategy, config.agent.memory_k)
        self.router = ConfidenceRouter(config.router.epsilon)
        self.agents = [ExperimentalAgent(f"agent_{index}") for index in range(config.experiment.num_agents)]
        assert_initial_symmetry(self.agents, config.agent.system_prompt)
        self.agent_by_id = {agent.agent_id: agent for agent in self.agents}
        self.task_rng = random.Random(
            config.experiment.task_seed if config.experiment.task_seed is not None else config.experiment.seed
        )
        self.router_rng = random.Random(
            config.experiment.router_seed
            if config.experiment.router_seed is not None
            else config.experiment.seed + 1
        )
        self.semaphore = asyncio.Semaphore(config.experiment.max_concurrency)
        self.route_history: list[dict[str, Any]] = []
        self.token_usages: list[dict[str, Any] | None] = []
        self.previous_probe_routing: list[str | None] | None = None
        self.last_metrics: dict[str, Any] | None = None

    @property
    def agent_ids(self) -> list[str]:
        return [agent.agent_id for agent in self.agents]

    @property
    def model_parameters(self) -> dict[str, Any]:
        return {
            "thinking": self.config.agent.thinking,
            "temperature": self.config.agent.temperature,
            "top_p": self.config.agent.top_p,
            "max_tokens": self.config.agent.max_tokens,
            "note": (
                "temperature/top_p/max_tokens are experimental metadata only for the OMP backend; "
                "OMP 17.2.10 does not document controls for them."
                if self.config.agent.backend == "omp"
                else "mock backend ignores decoding parameters"
            ),
        }

    @property
    def actual_model_label(self) -> str:
        return self.config.agent.model if self.config.agent.backend == "omp" else "mock/deterministic-modular-learner"

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
        records: list[InferenceRecord] = []
        final_error: str | None = None

        for attempt in range(self.config.experiment.technical_retries + 1):
            async with self.semaphore:
                backend_response = await self.backend.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=self.config.agent.model,
                    model_parameters=self.model_parameters,
                )
            parsed_answer: int | None = None
            confidence: float | None = None
            error = backend_response.error
            if error is None:
                if backend_response.raw_response is None:
                    error = "backend returned neither response text nor error"
                else:
                    try:
                        parsed = parse_agent_output(backend_response.raw_response)
                        parsed_answer, confidence = parsed.answer, parsed.confidence
                    except ResponseParseError as exc:
                        error = f"ResponseParseError: {exc}"
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
            )
            records.append(record)
            if error is None:
                return SolveResult(
                    agent_id=agent.agent_id,
                    response=AgentResponse(agent.agent_id, parsed_answer, confidence),
                    records=tuple(records),
                    memory_inserted=tuple(inserted),
                )
            final_error = error

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
        self, *, checkpoint: int, probes: Sequence[Task], probe_set_hash: str, logger: RunLogger
    ) -> dict[str, Any]:
        """Evaluate frozen snapshots; this function never calls ``observe``."""
        memory_before = {agent.agent_id: tuple(agent.memory) for agent in self.agents}
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
        flat_results = list(await asyncio.gather(*jobs))
        self._log_inferences(logger, flat_results)
        if any(tuple(agent.memory) != memory_before[agent.agent_id] for agent in self.agents):
            raise AssertionError("Probe evaluation mutated an agent memory")

        by_probe: list[list[SolveResult]] = [
            flat_results[index * len(self.agents) : (index + 1) * len(self.agents)]
            for index in range(len(probes))
        ]
        behavioral_matrix: list[list[int]] = [[] for _ in self.agents]
        observations: dict[str, list[ProbeObservation]] = {agent.agent_id: [] for agent in self.agents}
        probe_routing: list[str | None] = []
        for probe_index, (task, results) in enumerate(zip(probes, by_probe)):
            valid = [result.response for result in results if result.response is not None]
            probe_routing.append(self.router.deterministic_probe_choice(valid))
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
                "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
            },
        )
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
        mode = self.config.condition.memory_mode
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
        if mode == "no_memory":
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
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_id = (
            f"{self.config.condition.memory_mode}-seed{self.config.experiment.seed}-{timestamp}-{uuid.uuid4().hex[:8]}"
        )
        logger = RunLogger(self.config.logging.output_dir, run_id)
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
                    "probe_generation": "recorded in data/probe_set.json",
                },
                "backend": self.backend.metadata(),
                "scientific_controls": {
                    "agent_ids_are_host_side_only": True,
                    "same_system_prompt": True,
                    "empty_initial_memory": True,
                    "provider_session_independent": self.config.agent.backend == "omp",
                    "probe_updates_memory": False,
                    "hidden_rules_in_model_prompt": False,
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
        try:
            if 0 in self.config.experiment.checkpoints:
                await self._evaluate_checkpoint(
                    checkpoint=0, probes=probes, probe_set_hash=probe_set_hash, logger=logger
                )
            for round_id in range(1, self.config.experiment.num_rounds + 1):
                task = self.environment.sample_task(self.task_rng, task_id=f"round-{round_id}")
                memory_counts_before = {agent.agent_id: len(agent.memory) for agent in self.agents}
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
                if not valid:
                    logger.event(
                        "round_failed",
                        {
                            "round": round_id,
                            "task": task.experimenter_dict(),
                            "candidate_errors": {result.agent_id: result.error for result in results},
                        },
                    )
                    raise RuntimeError(f"Round {round_id}: no valid model response; no answer was invented")
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
                self.route_history.append({"world": task.world, "selected_agent_id": selected.agent_id})
                if self.config.experiment.console_summary:
                    self._print_round(round_id, task, results, memory_counts_before, selected, recipients)
                if round_id in self.config.experiment.checkpoints:
                    await self._evaluate_checkpoint(
                        checkpoint=round_id, probes=probes, probe_set_hash=probe_set_hash, logger=logger
                    )
            summary = {
                "run_id": run_id,
                "status": "completed",
                "condition": self.config.condition.memory_mode,
                "seed": self.config.experiment.seed,
                "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
                "routing_counts": dict(Counter(item["selected_agent_id"] for item in self.route_history)),
                "final_metrics": self.last_metrics,
                "usage": summarize_usage(
                    self.token_usages,
                    currency=self.config.cost.currency,
                    input_per_million_tokens=self.config.cost.input_per_million_tokens,
                    cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                    output_per_million_tokens=self.config.cost.output_per_million_tokens,
                ),
            }
            logger.write_summary(summary)
            if self.config.experiment.console_summary:
                self._print_final_summary(summary)
            return logger.run_dir
        except Exception as exc:
            logger.event("run_failed", {"error": f"{type(exc).__name__}: {exc}"})
            logger.write_summary(
                {
                    "run_id": run_id,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "memory_counts": {agent.agent_id: len(agent.memory) for agent in self.agents},
                    "usage": summarize_usage(
                        self.token_usages,
                        currency=self.config.cost.currency,
                        input_per_million_tokens=self.config.cost.input_per_million_tokens,
                        cached_input_per_million_tokens=self.config.cost.cached_input_per_million_tokens,
                        output_per_million_tokens=self.config.cost.output_per_million_tokens,
                    ),
                }
            )
            raise

    @staticmethod
    def _print_final_summary(summary: dict[str, Any]) -> None:
        metrics = summary.get("final_metrics") or {}
        print("\nFINAL SUMMARY")
        print(f"run: {summary['run_id']}")
        print(f"routing counts: {json.dumps(summary['routing_counts'], sort_keys=True)}")
        print(f"memory counts: {json.dumps(summary['memory_counts'], sort_keys=True)}")
        usage = summary.get("usage") or {}
        if usage.get("status") == "estimated":
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
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic MockBackend; no model calls")
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
    config = load_config(args.config).overridden(
        num_rounds=args.num_rounds,
        seed=args.seed,
        output_dir=args.output_dir,
        backend="mock" if args.dry_run else None,
    )
    run_dir = await ExperimentRunner(config).run()
    print(f"Raw events and metrics: {run_dir}")
    if args.report:
        from .reporting import generate_run_report

        report_dir = generate_run_report(run_dir, args.report_output)
        print(f"Executed notebook: {report_dir / 'report.ipynb'}")
        print(f"HTML report: {report_dir / 'report.html'}")
    return run_dir


def main(argv: Iterable[str] | None = None) -> None:
    asyncio.run(async_main(argv))


if __name__ == "__main__":
    main()

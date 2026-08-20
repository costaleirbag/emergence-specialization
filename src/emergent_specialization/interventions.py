"""Explicit, host-side interventions for causal memory/population studies.

The functions here operate on :class:`ExperimentalAgent` objects only. They do
not touch provider sessions and are disabled unless a config explicitly lists
an intervention.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence

from .agents import ExperimentalAgent
from .models import Experience


def memory_hash(memory: Sequence[Experience]) -> str:
    payload = [experience.prompt_dict() for experience in memory]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InterventionSpec:
    trigger_round: int
    operation: str
    source_agent: str | None = None
    target_agent: str | None = None
    worlds: tuple[str, ...] = ()
    replacement_agent: str | None = None

    def __post_init__(self) -> None:
        if self.trigger_round < 1:
            raise ValueError("interventions trigger before a round (trigger_round >= 1)")
        if self.operation not in {"memory_swap", "memory_erase", "memory_clone", "memory_transplant", "ablate_agent", "add_naive_agent", "replace_agent", "reintroduce_agent"}:
            raise ValueError(f"unsupported intervention operation: {self.operation}")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "InterventionSpec":
        worlds = value.get("worlds", ())
        if isinstance(worlds, str) or worlds is None:
            worlds = (worlds,) if worlds else ()
        if not isinstance(worlds, (list, tuple)):
            raise ValueError("intervention worlds must be a list")
        return cls(
            trigger_round=int(value.get("trigger_round", 0)),
            operation=str(value.get("operation", "")),
            source_agent=str(value["source_agent"]) if value.get("source_agent") is not None else None,
            target_agent=str(value["target_agent"]) if value.get("target_agent") is not None else None,
            worlds=tuple(str(world) for world in worlds),
            replacement_agent=str(value["replacement_agent"]) if value.get("replacement_agent") is not None else None,
        )


def _agents_by_id(agents: Iterable[ExperimentalAgent] | Mapping[str, ExperimentalAgent]) -> MutableMapping[str, ExperimentalAgent]:
    return dict(agents) if isinstance(agents, Mapping) else {agent.agent_id: agent for agent in agents}


def _require(mapping: Mapping[str, ExperimentalAgent], agent_id: str | None, role: str) -> ExperimentalAgent:
    if not agent_id:
        raise ValueError(f"{role} agent is required")
    try:
        return mapping[agent_id]
    except KeyError as exc:
        raise KeyError(f"unknown {role} agent: {agent_id}") from exc


def _replace_worlds(memory: Sequence[Experience], selected_worlds: set[str], replacement: Sequence[Experience]) -> list[Experience]:
    replacement_iter = iter(replacement)
    result: list[Experience] = []
    for experience in memory:
        if experience.world in selected_worlds:
            try:
                result.append(next(replacement_iter))
            except StopIteration:
                continue
        else:
            result.append(experience)
    result.extend(item for item in replacement_iter)
    return result


def _memory_payload(agent: ExperimentalAgent) -> dict[str, object]:
    return {"agent": agent.agent_id, "count": len(agent.memory), "hash": memory_hash(agent.memory)}


def apply_memory_intervention(
    agents: Iterable[ExperimentalAgent] | Mapping[str, ExperimentalAgent], spec: InterventionSpec
) -> dict[str, object]:
    """Apply a memory operation and return an auditable before/after payload."""
    mapping = _agents_by_id(agents)
    source = _require(mapping, spec.source_agent, "source") if spec.source_agent else None
    target_id = spec.target_agent or spec.source_agent
    target = _require(mapping, target_id, "target") if target_id else None
    touched = [agent for agent in (source, target) if agent is not None]
    before = [_memory_payload(agent) for agent in touched]
    selected_worlds = set(spec.worlds)
    if spec.operation == "memory_swap":
        assert source is not None and target is not None
        if source is target:
            raise ValueError("memory_swap requires distinct agents")
        if selected_worlds:
            source_selected = [item for item in source.memory if item.world in selected_worlds]
            target_selected = [item for item in target.memory if item.world in selected_worlds]
            source.memory = _replace_worlds(source.memory, selected_worlds, target_selected)
            target.memory = _replace_worlds(target.memory, selected_worlds, source_selected)
        else:
            source.memory, target.memory = list(target.memory), list(source.memory)
    elif spec.operation == "memory_erase":
        assert target is not None
        if selected_worlds:
            target.memory = [item for item in target.memory if item.world not in selected_worlds]
        else:
            target.memory.clear()
    elif spec.operation == "memory_clone":
        assert source is not None and target is not None
        if selected_worlds:
            clone = [item for item in source.memory if item.world in selected_worlds]
            target.memory = _replace_worlds(target.memory, selected_worlds, clone)
        else:
            target.memory = list(source.memory)
    elif spec.operation == "memory_transplant":
        assert source is not None and target is not None and selected_worlds
        clone = [item for item in source.memory if item.world in selected_worlds]
        target.memory = _replace_worlds(target.memory, selected_worlds, clone)
    else:
        raise ValueError(f"not a memory intervention: {spec.operation}")
    after = [_memory_payload(agent) for agent in touched]
    return {
        "event": "intervention",
        "operation": spec.operation,
        "trigger_round": spec.trigger_round,
        "source_agent": spec.source_agent,
        "target_agent": spec.target_agent,
        "worlds": list(spec.worlds),
        "before": before,
        "after": after,
    }


@dataclass
class PopulationState:
    """Safe population bookkeeping, intentionally not wired into fixed-N metrics."""

    active: dict[str, ExperimentalAgent]
    removed: dict[str, ExperimentalAgent] | None = None

    def __post_init__(self) -> None:
        if self.removed is None:
            self.removed = {}

    def ablate_agent(self, agent_id: str) -> ExperimentalAgent:
        try:
            agent = self.active.pop(agent_id)
        except KeyError as exc:
            raise KeyError(f"unknown active agent: {agent_id}") from exc
        assert self.removed is not None
        self.removed[agent_id] = agent
        return agent

    def add_naive_agent(self, agent_id: str) -> ExperimentalAgent:
        if agent_id in self.active or (self.removed and agent_id in self.removed):
            raise ValueError(f"agent ID already exists: {agent_id}")
        agent = ExperimentalAgent(agent_id)
        self.active[agent_id] = agent
        return agent

    def replace_agent(self, old_agent_id: str, new_agent_id: str) -> ExperimentalAgent:
        self.ablate_agent(old_agent_id)
        return self.add_naive_agent(new_agent_id)

    def reintroduce_agent(self, agent_id: str) -> ExperimentalAgent:
        assert self.removed is not None
        try:
            agent = self.removed.pop(agent_id)
        except KeyError as exc:
            raise KeyError(f"unknown removed agent: {agent_id}") from exc
        self.active[agent_id] = agent
        return agent


def apply_population_intervention(state: PopulationState, spec: InterventionSpec) -> dict[str, object]:
    if spec.operation == "ablate_agent":
        agent = state.ablate_agent(spec.target_agent or spec.source_agent or "")
        return {"event": "population_change", "operation": spec.operation, "agent": agent.agent_id, "active_agents": sorted(state.active)}
    if spec.operation == "add_naive_agent":
        agent_id = spec.replacement_agent or spec.target_agent
        if not agent_id:
            raise ValueError("add_naive_agent requires replacement_agent or target_agent")
        agent = state.add_naive_agent(agent_id)
        return {"event": "population_change", "operation": spec.operation, "agent": agent.agent_id, "active_agents": sorted(state.active)}
    if spec.operation == "replace_agent":
        old = spec.source_agent or spec.target_agent
        new = spec.replacement_agent
        if not old or not new:
            raise ValueError("replace_agent requires source_agent and replacement_agent")
        agent = state.replace_agent(old, new)
        return {"event": "population_change", "operation": spec.operation, "removed": old, "added": agent.agent_id, "active_agents": sorted(state.active)}
    if spec.operation == "reintroduce_agent":
        agent = state.reintroduce_agent(spec.target_agent or spec.source_agent or "")
        return {"event": "population_change", "operation": spec.operation, "agent": agent.agent_id, "active_agents": sorted(state.active)}
    raise ValueError(f"not a population intervention: {spec.operation}")

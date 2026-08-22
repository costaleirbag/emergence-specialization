"""Frozen ecology constructors used by Theory V1 manifests and mock tests."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Any

from emergent_specialization.studies.ecology.ecological_information import FAMILIES as V31_FAMILIES
from emergent_specialization.studies.ecology.ecological_information import generate_environment, solve
from emergent_specialization.studies.ecology.ecological_information_v31 import EVAL_TEMPLATE_IDS, TRAIN_TEMPLATE_IDS, observable_o, render_observable


@dataclass(frozen=True)
class ResolvedCase:
    niche: int
    x: tuple[int, ...]
    y: tuple[int, ...]
    template_id: int
    role: str


class V31Fresh:
    name = "V31_FRESH"
    niches = tuple(V31_FAMILIES)

    @classmethod
    def resolved(cls, seed: int, niche: int, x: tuple[int, int, int], role: str = "training") -> ResolvedCase:
        environment = generate_environment("DIAGONAL", seed)
        family = cls.niches[niche]
        return ResolvedCase(niche=niche, x=x, y=tuple(solve(environment.theta_by_family[family], x)), template_id=TRAIN_TEMPLATE_IDS[0] if role == "training" else EVAL_TEMPLATE_IDS[0], role=role)

    @classmethod
    def render(cls, case: ResolvedCase) -> str:
        family = cls.niches[case.niche]
        return render_observable(observable_o(family, tuple(case.x)), family, case.template_id)


class AffineBooleanV1:
    name = "AFFINE_BOOLEAN_V1"
    niches = ("ACCESS", "INCIDENT", "PROVENANCE", "RELEASE")
    # Distinct, nonconstant subsets.  The semantic renderer intentionally does
    # not expose these policy parameters.
    _policies = (
        ((0, 2), (1,), (3, 4)),
        ((1, 3), (0, 5), (2,)),
        ((0,), (2, 4), (1, 5)),
        ((3,), (0, 2), (4, 5)),
    )

    @classmethod
    def policy(cls, seed: int, niche: int) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
        rng = random.Random(seed * 1009 + niche * 9176)
        offsets = tuple(rng.randrange(2) for _ in range(3))
        subsets = cls._policies[niche]
        return offsets, tuple(subsets)

    @classmethod
    def solve(cls, seed: int, niche: int, x: tuple[int, ...]) -> tuple[int, int, int]:
        offsets, subsets = cls.policy(seed, niche)
        return tuple((offsets[j] + sum(x[index] for index in subset)) % 2 for j, subset in enumerate(subsets))  # type: ignore[return-value]

    @classmethod
    def resolved(cls, seed: int, niche: int, x: tuple[int, ...], role: str = "training") -> ResolvedCase:
        return ResolvedCase(niche=niche, x=x, y=cls.solve(seed, niche, x), template_id=0, role=role)

    @classmethod
    def render(cls, case: ResolvedCase) -> str:
        labels = ("status", "context", "signal", "constraint", "history", "priority")
        attrs = ", ".join(f"{labels[i]}={'active' if value else 'inactive'}" for i, value in enumerate(case.x))
        return f"A neutral operational case has six observable attributes: {attrs}. Return the three binary decisions in order."


def fresh_training_state(ecology: str, seed: int, k: int) -> list[ResolvedCase]:
    """Construct a balanced, training-only memory in a deterministic order."""
    constructor = V31Fresh if ecology == V31Fresh.name else AffineBooleanV1 if ecology == AffineBooleanV1.name else None
    if constructor is None:
        raise ValueError(ecology)
    rng = random.Random(seed * 7919 + k)
    states = []
    per_niche = k // 4
    support = list(itertools.product(range(4), repeat=3)) if constructor is V31Fresh else list(itertools.product(range(2), repeat=6))
    for niche in range(4):
        for index in range(per_niche):
            x = support[(seed + niche * 17 + index * 7) % len(support)]
            states.append(constructor.resolved(seed, niche, x, "training"))
    rng.shuffle(states)
    return states

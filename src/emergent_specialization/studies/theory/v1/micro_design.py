"""Frozen, provider-independent Theory V1 micro design and call accounting."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass
from typing import Any, Iterable

ECOLOGIES = ("V31_FRESH", "AFFINE_BOOLEAN_V1")
K_VALUES = (4, 8, 12)
MICRO_SEEDS = {
    "V31_FRESH": tuple(range(73101, 73109)),
    "AFFINE_BOOLEAN_V1": tuple(range(83101, 83109)),
}
SOCIAL_SEEDS = {
    "V31_FRESH": tuple(range(73201, 73209)),
    "AFFINE_BOOLEAN_V1": tuple(range(83201, 83209)),
}
N_AGENTS = 4
N_NICHES = 4
PROBES_PER_NICHE = 8
MICRO_MEMORY_STATES = 17
MICRO_CALLS_PER_UNIT = MICRO_MEMORY_STATES * N_NICHES * PROBES_PER_NICHE
MACRO_BETAS = (0.0, 4.0, 8.0, 12.0, 20.0)
MACRO_CELLS = 18
MACRO_ROUNDS = 128
MACRO_CHECKPOINTS = (0, 16, 32, 64, 128)
MACRO_CALLS_PER_CELL = MACRO_ROUNDS + (len(MACRO_CHECKPOINTS) - 1) * N_AGENTS * N_NICHES * PROBES_PER_NICHE


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def expected_call_counts() -> dict[str, int]:
    micro = sum(len(seeds) for seeds in MICRO_SEEDS.values()) * len(K_VALUES) * MICRO_CALLS_PER_UNIT
    macro = sum(len(seeds) for seeds in SOCIAL_SEEDS.values()) * (N_AGENTS * N_NICHES * PROBES_PER_NICHE + MACRO_CELLS * MACRO_CALLS_PER_CELL)
    return {"micro": micro, "macro": macro, "total": micro + macro, "micro_unit": MICRO_CALLS_PER_UNIT, "macro_cell": MACRO_CALLS_PER_CELL}


def balanced_memory(seed: int, k: int, niches: int = N_NICHES) -> list[dict[str, int]]:
    if k % niches:
        raise ValueError("k must be divisible by number of niches")
    values = [niche for niche in range(niches) for _ in range(k // niches)]
    random.Random(seed).shuffle(values)
    return [{"niche": value, "slot": slot} for slot, value in enumerate(values)]


def single_swaps(seed: int, k: int, niches: int = N_NICHES) -> list[dict[str, Any]]:
    base = balanced_memory(seed, k, niches)
    swaps = []
    for source, target in itertools.permutations(range(niches), 2):
        eligible = [item["slot"] for item in base if item["niche"] == source]
        slot = eligible[(source + target + seed) % len(eligible)]
        swaps.append({"source": source, "target": target, "slot": slot})
    return swaps


def double_swaps(seed: int, k: int, niches: int = N_NICHES) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    swaps = single_swaps(seed, k, niches)
    pairs = []
    for left, right in itertools.combinations(swaps, 2):
        if left["slot"] != right["slot"] and left["source"] != right["source"] and left["target"] != right["target"]:
            pairs.append((left, right))
    if len(pairs) < 4:
        raise AssertionError("deterministic double-swap design is underfull")
    return pairs[:4]


def micro_manifest() -> dict[str, Any]:
    counts = expected_call_counts()
    units = []
    for ecology in ECOLOGIES:
        for seed in MICRO_SEEDS[ecology]:
            for k in K_VALUES:
                units.append({"ecology": ecology, "seed": seed, "k": k, "memory_hash": stable_hash(balanced_memory(seed, k)), "single_swaps": single_swaps(seed, k), "double_swaps": double_swaps(seed, k)})
    return {"protocol": "THEORY-V1", "ecologies": ECOLOGIES, "units": units, "expected_calls": counts, "micro_only": True}


def macro_cells() -> list[dict[str, Any]]:
    cells = []
    for k in K_VALUES:
        for beta in MACRO_BETAS:
            cells.append({"k": k, "beta": beta, "epsilon": 0.10, "q_share": 0.0})
    cells.extend([
        {"k": 8, "beta": 12.0, "epsilon": 0.10, "q_share": 0.50},
        {"k": 8, "beta": 12.0, "epsilon": 0.10, "q_share": 1.00},
        {"k": 8, "beta": 16.0, "epsilon": 0.55, "q_share": 0.0},
    ])
    return cells

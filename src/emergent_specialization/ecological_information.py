"""Offline ecological information geometry instrument (V3).

This module is intentionally independent of the LLM/society execution path.  It
generates a small exact procedural ecology, computes the predictive information
available to an ideal Bayesian learner, and writes auditable CSV/JSON reports.
No provider, credential, or network code is imported here.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import statistics
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .semantic_ecology import GEOMETRY_ECOLOGIES, stable_hash
def _old_natural_cases(ecology: Any, environment: Any, family: str, *, h: int) -> list[Any]:
    """Reproduce the frozen V2 ordinary (non-teaching) stream locally."""
    pool = ecology.case_pool(environment, family, template="train")
    rng = random.Random(0xA71CE + environment.seed * 104729 + sum(ord(x) for x in family) * 31)
    rng.shuffle(pool)
    return pool[:h]

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/task-ecology/ecological-information-v3"
V2_REPORT_ROOT = ROOT / "reports/task-ecology/transfer-geometry-v1"
FAMILIES = ("ACCESS", "RELEASE", "INCIDENT", "PROVENANCE")
GEOMETRIES = ("GLOBAL", "BLOCK", "DIAGONAL")
HORIZONS = (0, 1, 2, 4, 8)
INPUT_VALUES = (0, 1, 2, 3)
V3_SEEDS = tuple(range(10))
MC_DRAWS = 10_000
ALGORITHM_VERSION = "v3-bayes-ig-3"


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fields or sorted({k for row in rows for k in row}))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# The six balanced Boolean maps on four input symbols.  A map is a tuple in
# input-value order, and has exactly two zeros and two ones.
BALANCED_MAPS: tuple[tuple[int, int, int, int], ...] = tuple(
    bits for bits in itertools.product((0, 1), repeat=4) if sum(bits) == 2
)


@dataclass(frozen=True)
class V3Case:
    family: str
    x: tuple[int, int, int]
    y: tuple[int, int, int]

    @property
    def case_id(self) -> str:
        return f"{self.family}:{''.join(map(str, self.x))}"

    def symbolic(self) -> dict[str, Any]:
        return {"family": self.family, "x": list(self.x), "y": list(self.y)}


@dataclass(frozen=True)
class V3Environment:
    geometry: str
    seed: int
    theta_by_family: dict[str, tuple[tuple[int, int, int, int], ...]]
    group_by_family: dict[str, int]

    def theta_hash(self) -> str:
        return stable_hash({k: self.theta_by_family[k] for k in FAMILIES})


def _groups(geometry: str) -> dict[str, int]:
    if geometry == "GLOBAL":
        return {f: 0 for f in FAMILIES}
    if geometry == "BLOCK":
        return {"ACCESS": 0, "RELEASE": 0, "INCIDENT": 1, "PROVENANCE": 1}
    if geometry == "DIAGONAL":
        return {f: i for i, f in enumerate(FAMILIES)}
    raise ValueError(f"unknown geometry {geometry}")


def generate_environment(geometry: str, seed: int) -> V3Environment:
    """Generate a V3 environment without exposing theta in semantic text."""
    groups = _groups(geometry)
    rng = random.Random(0xE1C0_3A + seed * 7919)
    group_theta = {group: tuple(rng.choice(BALANCED_MAPS) for _ in range(3))
                   for group in sorted(set(groups.values()))}
    theta = {family: group_theta[group] for family, group in groups.items()}
    return V3Environment(geometry, seed, theta, groups)


def all_symbolic_cases(family: str) -> list[V3Case]:
    if family not in FAMILIES:
        raise ValueError(family)
    return [V3Case(family, x, (0, 0, 0)) for x in itertools.product(INPUT_VALUES, repeat=3)]


def solve(theta: tuple[tuple[int, int, int, int], ...], x: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(theta[j][x[j]] for j in range(3))


def solved_case(environment: V3Environment, family: str, x: tuple[int, int, int]) -> V3Case:
    return V3Case(family, x, solve(environment.theta_by_family[family], x))


def render_case(case: V3Case) -> str:
    """Natural surface; no geometry, theta, factor, or hidden-label leakage."""
    return ("A generated organizational case contains three independent policy signals. "
            f"Signal A is level {case.x[0]}, signal B is level {case.x[1]}, and signal C is level {case.x[2]}. "
            "Return the three binary policy decisions in order as a JSON array.")


def sample_history(environment: V3Environment, source: str, h: int, rng: random.Random) -> list[V3Case]:
    return [solved_case(environment, source, tuple(rng.randrange(4) for _ in range(3))) for _ in range(h)]


def teaching_history(environment: V3Environment, source: str, h: int) -> list[V3Case]:
    """Greedy deterministic information-gain teaching sequence (optional control)."""
    remaining = [list(BALANCED_MAPS) for _ in range(3)]
    chosen: list[V3Case] = []
    unused = list(itertools.product(INPUT_VALUES, repeat=3))
    for _ in range(h):
        if not unused:
            break
        def information_score(candidate: tuple[int, int, int]) -> tuple[float, tuple[int, int, int]]:
            reduction = 0.0
            for j in range(3):
                prior = len(remaining[j])
                truth = environment.theta_by_family[source][j][candidate[j]]
                after = sum(m[candidate[j]] == truth for m in remaining[j])
                reduction += math.log2(prior) - math.log2(after or 1)
            return reduction, tuple(-v for v in candidate)
        x = max(unused, key=information_score)
        unused.remove(x)
        case = solved_case(environment, source, x)
        chosen.append(case)
        for j in range(3):
            remaining[j] = [m for m in remaining[j] if m[x[j]] == case.y[j]]
    return chosen


def _posterior_for_group(history: Iterable[V3Case], source: str, group: int, env: V3Environment) -> tuple[tuple[float, ...], ...]:
    relevant = [obs for obs in history if env.group_by_family[source] == group]
    result: list[tuple[float, ...]] = []
    for j in range(3):
        consistent = [m for m in BALANCED_MAPS if all(m[o.x[j]] == o.y[j] for o in relevant)]
        weights = tuple((1.0 / len(consistent) if m in consistent else 0.0) for m in BALANCED_MAPS)
        result.append(weights)
    return tuple(result)


def posterior_predictive(environment: V3Environment, source: str, target: str,
                         history: Iterable[V3Case], x: tuple[int, int, int]) -> tuple[float, ...]:
    """Exact eight-class posterior predictive probabilities."""
    history = list(history)
    groups = _groups(environment.geometry)
    by_group = {g: _posterior_for_group(history, source, g, environment) for g in set(groups.values())}
    bit_probs = []
    for j in range(3):
        posterior = by_group[groups[target]][j]
        bit_probs.append(sum(w * m[x[j]] for w, m in zip(posterior, BALANCED_MAPS)))
    probs = []
    for y in itertools.product((0, 1), repeat=3):
        p = 1.0
        for bit, q in zip(y, bit_probs):
            p *= q if bit else 1.0 - q
        probs.append(p)
    return tuple(probs)


def entropy_bits(probs: Iterable[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0.0)


def _stats_for_history(environment: V3Environment, source: str, target: str,
                       history: list[V3Case]) -> tuple[float, float, float, float]:
    """(J contribution, joint Bayes accuracy, component accuracy, entropy)."""
    entropies: list[float] = []
    joint_acc: list[float] = []
    component_acc: list[float] = []
    for x in itertools.product(INPUT_VALUES, repeat=3):
        p = posterior_predictive(environment, source, target, history, x)
        entropies.append(entropy_bits(p))
        joint_acc.append(max(p))
        bit_acc = []
        for j in range(3):
            q = sum(p[index] for index, y in enumerate(itertools.product((0, 1), repeat=3)) if y[j])
            bit_acc.append(max(q, 1.0 - q))
        component_acc.append(statistics.mean(bit_acc))
    residual = statistics.mean(entropies)
    return 3.0 - residual, statistics.mean(joint_acc), statistics.mean(component_acc), residual


def _stats_from_posteriors(posteriors: tuple[tuple[float, ...], ...]) -> tuple[float, float, float, float]:
    """Same statistic as ``_stats_for_history`` but cacheable by posterior."""
    entropies: list[float] = []
    joint_acc: list[float] = []
    component_acc: list[float] = []
    for x in itertools.product(INPUT_VALUES, repeat=3):
        bit_probs = [sum(w * m[x[j]] for w, m in zip(posteriors[j], BALANCED_MAPS)) for j in range(3)]
        p = []
        for y in itertools.product((0, 1), repeat=3):
            q = 1.0
            for bit, prob in zip(y, bit_probs):
                q *= prob if bit else 1.0 - prob
            p.append(q)
        entropies.append(entropy_bits(p)); joint_acc.append(max(p))
        component_acc.append(statistics.mean(max(q, 1.0 - q) for q in bit_probs))
    residual = statistics.mean(entropies)
    return 3.0 - residual, statistics.mean(joint_acc), statistics.mean(component_acc), residual


def _baseline_stats() -> tuple[float, float, float]:
    # Uniform prior over balanced maps makes each output bit and each joint
    # three-bit output uniform before observing any history.
    return 0.0, 1.0 / 8.0, 0.5


def estimate_v3(draws: int = MC_DRAWS, *, horizons: Sequence[int] = HORIZONS,
                seed_values: Sequence[int] = V3_SEEDS, include_teaching: bool = True) -> list[dict[str, Any]]:
    """Estimate J and Bayes L* by deterministic MC over the known ecology prior."""
    if draws < 1:
        raise ValueError("draws must be positive")
    rows: list[dict[str, Any]] = []
    cache: dict[tuple[Any, ...], tuple[float, float, float, float]] = {}
    for geometry in GEOMETRIES:
        for source in FAMILIES:
            for target in FAMILIES:
                for h in horizons:
                    policies = ("natural", "teaching") if include_teaching and h > 0 else ("natural",)
                    for policy in policies:
                        total_j = total_acc = total_comp = total_ent = 0.0
                        for draw in range(draws):
                            env_seed = seed_values[draw % len(seed_values)] + draw * 100_003
                            env = generate_environment(geometry, env_seed)
                            rng = random.Random(0x51A7 + env_seed * 1009 + sum(map(ord, source)) * 17 + h * 31)
                            history = sample_history(env, source, h, rng) if policy == "natural" else teaching_history(env, source, h)
                            # The posterior depends only on the observable history and
                            # target group.  Cache repeated signatures for speed.
                            groups = _groups(geometry)
                            target_post = _posterior_for_group(history, source, groups[target], env)
                            signature = (geometry, target, target_post)
                            if signature not in cache:
                                cache[signature] = _stats_from_posteriors(target_post)
                            j, acc, comp, ent = cache[signature]
                            total_j += j; total_acc += acc; total_comp += comp; total_ent += ent
                        _, base_acc, base_comp = _baseline_stats()
                        rows.append({"geometry": geometry, "source": source, "target": target, "h": h,
                                     "policy": policy, "draws": draws,
                                     "J_bits": total_j / draws,
                                     "J_normalized": (total_j / draws) / 3.0,
                                     "bayes_accuracy": total_acc / draws,
                                     "L_star": total_acc / draws - base_acc,
                                     "component_accuracy": total_comp / draws,
                                     "component_L_star": total_comp / draws - base_comp,
                                     "conditional_entropy_bits": total_ent / draws,
                                     "mc_seed_hash": stable_hash(list(seed_values))})
    return rows


def geometry_summary(rows: list[dict[str, Any]], *, horizon: int = 8, policy: str = "natural") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    def mean_or_zero(values: list[float]) -> float:
        return statistics.mean(values) if values else 0.0
    for geometry in GEOMETRIES:
        vals = {(r["source"], r["target"]): r for r in rows if r["geometry"] == geometry and r["h"] == horizon and r["policy"] == policy}
        diag = [vals[(f, f)]["J_normalized"] for f in FAMILIES]
        off = [vals[(s, t)]["J_normalized"] for s in FAMILIES for t in FAMILIES if s != t]
        within = [vals[(s, t)]["J_normalized"] for s, t in (("ACCESS", "RELEASE"), ("RELEASE", "ACCESS"), ("INCIDENT", "PROVENANCE"), ("PROVENANCE", "INCIDENT"))]
        cross = [vals[(s, t)]["J_normalized"] for s in FAMILIES for t in FAMILIES if s != t and _groups(geometry)[s] != _groups(geometry)[t]]
        ldiag = [vals[(f, f)]["L_star"] for f in FAMILIES]
        loff = [vals[(s, t)]["L_star"] for s in FAMILIES for t in FAMILIES if s != t]
        out.append({"geometry": geometry, "h": horizon, "policy": policy,
                    "D_J": mean_or_zero(diag), "O_J": mean_or_zero(off),
                    "Q_J": mean_or_zero(diag) - mean_or_zero(off),
                    "W_J": mean_or_zero(within), "C_J": mean_or_zero(cross),
                    "D_L_star": mean_or_zero(ldiag), "O_L_star": mean_or_zero(loff),
                    "Q_L_star": mean_or_zero(ldiag) - mean_or_zero(loff),
                    "G_hash": stable_hash([[int(_groups(geometry)[s] == _groups(geometry)[t]) for t in FAMILIES] for s in FAMILIES])})
    return out


def old_construct_validity_audit(sweep: int = 10_000) -> dict[str, list[dict[str, Any]]]:
    """Offline audit of what V2 generated, not what metadata intended."""
    collision_rows: list[dict[str, Any]] = []
    influence_rows: list[dict[str, Any]] = []
    agreement_rows: list[dict[str, Any]] = []
    ident_rows: list[dict[str, Any]] = []
    fields = list(itertools.product((1, 2, 3), ("operator", "owner", "reviewer", "visitor"),
                                     ("operator", "owner", "archive", "service"), ("approved", "pending"),
                                     (False, True), (False, True), (False, True)))
    field_dicts = [{"criticality": c, "role": r, "resource": q, "approval": a, "provenance": p,
                    "temporal_valid": t, "exception": e} for c, r, q, a, p, t, e in fields]
    for geometry in GEOMETRIES:
        ecology = GEOMETRY_ECOLOGIES[geometry]
        for seed in range(sweep):
            env = ecology.generate_environment(seed)
            for i, source in enumerate(FAMILIES):
                for target in FAMILIES[i + 1:]:
                    fs = env.metadata["factor_ids_by_family"][source]; ft = env.metadata["factor_ids_by_family"][target]
                    shared = len(set(fs) & set(ft)); equal = sum(env.metadata["factor_values"][a] == env.metadata["factor_values"][b] for a, b in zip(fs, ft)) / 3.0
                    collision_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target,
                                           "shared_factor_count": shared, "same_position_value_fraction": equal,
                                           "all_three_values_equal": int(all(env.metadata["factor_values"][a] == env.metadata["factor_values"][b] for a, b in zip(fs, ft)))})
        # The 10,000-seed sweep is intentionally limited to realized collision
        # frequencies.  Full symbolic counterfactual influence is evaluated on
        # the five frozen campaign environments below (otherwise it needlessly
        # repeats 10k * 4 * 3 * 768 solver calls).
        # Natural identifiability over the frozen five seeds, h=1,2,4,8.
        for seed in (8101, 8102, 8103, 8104, 8105):
            env = ecology.generate_environment(seed)
            for family in FAMILIES:
                actual = env.theta[family]
                for factor in env.metadata["factor_ids_by_family"][family]:
                    changed = 0
                    alt_values = (2, 3) if factor.endswith("threshold") else (("strict", "broad") if factor.endswith("compatibility") else ("ESCALATE", "DENY"))
                    alt = next(v for v in alt_values if v != env.metadata["factor_values"][factor])
                    theta = dict(actual); key = "threshold" if factor.endswith("threshold") else "compatibility" if factor.endswith("compatibility") else "exception"; theta[key] = alt
                    for fd in field_dicts:
                        if ecology.solve_with_theta(actual, family, fd) != ecology.solve_with_theta(theta, family, fd): changed += 1
                    influence_rows.append({"geometry": geometry, "seed": seed, "family": family, "factor_id": factor,
                                           "C_j": changed / len(field_dicts), "changed_cases": changed, "total_cases": len(field_dicts)})
            for family in FAMILIES:
                for h in (1, 2, 4, 8):
                    cases = _old_natural_cases(ecology, env, family, h=h)
                    candidates = ecology.candidate_thetas(family, env)
                    consistent = [theta for theta in candidates if all(ecology.solve_with_theta(theta, family, c.fields) == c.expected for c in cases)]
                    probes = ecology.probe_cases(env, family)
                    predictions = [len({ecology.solve_with_theta(t, family, p.fields) for t in consistent}) <= 1 for p in probes] if consistent else [False] * len(probes)
                    ident_rows.append({"geometry": geometry, "seed": seed, "family": family, "h": h,
                                       "candidate_count": len(candidates), "consistent_count": len(consistent),
                                       "predictive_identifiability": statistics.mean(predictions), "natural_case_count": len(cases)})
        # Agreement over the complete symbolic input space for the frozen seeds.
        for seed in (8101, 8102, 8103, 8104, 8105):
            env = ecology.generate_environment(seed)
            for source in FAMILIES:
                for target in FAMILIES:
                    a = [ecology.solve(env, source, fd) for fd in field_dicts]; b = [ecology.solve(env, target, fd) for fd in field_dicts]
                    agreement_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target,
                                           "functional_agreement": statistics.mean(x == y for x, y in zip(a, b)), "input_count": len(field_dicts)})
    return {"collision": collision_rows, "influence": influence_rows, "agreement": agreement_rows, "identifiability": ident_rows,
            "information": _old_information_rows()}


def _old_information_rows() -> list[dict[str, Any]]:
    """Finite empirical-prior J/L* diagnostic for the five frozen V1 seeds.

    This is intentionally not the V3 prior: it conditions on the exact five
    generated OPE environments and therefore is a retrospective descriptive
    audit, not evidence of a population-level information law.
    """
    rows: list[dict[str, Any]] = []
    seeds = (8101, 8102, 8103, 8104, 8105)
    field_dicts = [{"criticality": c, "role": r, "resource": q, "approval": a, "provenance": p,
                    "temporal_valid": t, "exception": e}
                   for c, r, q, a, p, t, e in itertools.product((1, 2, 3), ("operator", "owner", "reviewer", "visitor"),
                     ("operator", "owner", "archive", "service"), ("approved", "pending"), (False, True), (False, True), (False, True))]
    for geometry in GEOMETRIES:
        ecology = GEOMETRY_ECOLOGIES[geometry]
        envs = {s: ecology.generate_environment(s) for s in seeds}
        for source in FAMILIES:
            for target in FAMILIES:
                prior_outputs = [[ecology.solve(envs[s], target, fd) for s in seeds] for fd in field_dicts]
                h0 = statistics.mean(entropy_bits([values.count(label) / len(values) for label in ecology.output_classes]) for values in prior_outputs)
                a0 = statistics.mean(max(values.count(label) / len(values) for label in ecology.output_classes) for values in prior_outputs)
                for h in (4, 8):
                    residuals: list[float] = []; accuracies: list[float] = []
                    for source_seed in seeds:
                        history = _old_natural_cases(ecology, envs[source_seed], source, h=h)
                        consistent = [s for s in seeds if all(ecology.solve(envs[s], source, c.fields) == c.expected for c in history)]
                        if not consistent:
                            consistent = [source_seed]
                        target_ent = []; target_acc = []
                        for values in prior_outputs:
                            posterior = [values[seeds.index(s)] for s in consistent]
                            target_ent.append(entropy_bits([posterior.count(label) / len(posterior) for label in ecology.output_classes]))
                            target_acc.append(max(posterior.count(label) / len(posterior) for label in ecology.output_classes))
                        residuals.append(statistics.mean(target_ent)); accuracies.append(statistics.mean(target_acc))
                    j = h0 - statistics.mean(residuals); a = statistics.mean(accuracies)
                    rows.append({"geometry": geometry, "source": source, "target": target, "h": h,
                                 "empirical_prior_seeds": len(seeds), "J_bits": j, "J_normalized": j / math.log2(len(ecology.output_classes)),
                                 "bayes_accuracy": a, "L_star": a - a0, "baseline_accuracy": a0,
                                 "note": "retrospective five-seed empirical prior; not V3 Bayes result"})
    return rows


def write_v3_reports(*, draws: int = MC_DRAWS) -> dict[str, Any]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    old = old_construct_validity_audit()
    _write_csv(REPORT_ROOT / "old_parameter_collision.csv", old["collision"])
    _write_csv(REPORT_ROOT / "old_factor_influence.csv", old["influence"])
    _write_csv(REPORT_ROOT / "old_functional_agreement.csv", old["agreement"])
    _write_csv(REPORT_ROOT / "old_natural_identifiability.csv", old["identifiability"])
    _write_csv(REPORT_ROOT / "old_natural_information.csv", old["information"])
    existing_manifest = REPORT_ROOT / "v3_manifest.json"
    existing_rows = REPORT_ROOT / "v3_J_Lstar.csv"
    if existing_manifest.exists() and existing_rows.exists():
        try:
            prior = json.loads(existing_manifest.read_text(encoding="utf-8"))
            rows = [dict(r) for r in csv.DictReader(existing_rows.open(encoding="utf-8"))] if int(prior.get("draws", -1)) == draws and prior.get("algorithm_version") == ALGORITHM_VERSION else estimate_v3(draws)
            # CSV values are strings; normalize the numeric fields used below.
            for row in rows:
                for key in ("h", "draws", "J_bits", "J_normalized", "bayes_accuracy", "L_star", "component_accuracy", "component_L_star", "conditional_entropy_bits"):
                    if key in row:
                        row[key] = int(row[key]) if key in {"h", "draws"} else float(row[key])
        except (OSError, ValueError, json.JSONDecodeError):
            rows = estimate_v3(draws)
    else:
        rows = estimate_v3(draws)
    _write_csv(REPORT_ROOT / "v3_J_Lstar.csv", rows)
    summaries = geometry_summary(rows)
    _write_csv(REPORT_ROOT / "v3_geometry_summary.csv", summaries)
    g_rows = []
    for geometry in GEOMETRIES:
        groups = _groups(geometry)
        for s in FAMILIES:
            for t in FAMILIES:
                g_rows.append({"geometry": geometry, "source": s, "target": t, "G": int(groups[s] == groups[t])})
    _write_csv(REPORT_ROOT / "v3_G.csv", g_rows)
    # Small dependency-free SVGs keep the audit inspectable on machines without
    # matplotlib.  They are figures, not publication styling.
    fig_dir = REPORT_ROOT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    for h in HORIZONS:
        for metric in ("J_normalized", "L_star"):
            for geometry in GEOMETRIES:
                vals = {(r["source"], r["target"]): float(r[metric]) for r in rows
                        if r["geometry"] == geometry and r["h"] == h and r["policy"] == "natural"}
                _svg_matrix(fig_dir / f"{geometry.lower()}_{metric}_h{h}.svg", vals,
                            f"{geometry} {metric} h={h}")
    _write_csv(REPORT_ROOT / "v3_gates.csv", _v3_gates(summaries, rows))
    manifest = {"protocol": "ECOLOGICAL-INFORMATION-GEOMETRY-V3", "created_at_utc": _now(),
                "draws": draws, "algorithm_version": ALGORITHM_VERSION, "horizons": list(HORIZONS), "families": list(FAMILIES),
                "geometries": list(GEOMETRIES), "balanced_map_count": len(BALANCED_MAPS),
                "external_model_calls": 0, "external_spend_usd": 0.0,
                "draw_policy": "deterministic MC; 2000 minimum used because 10000 was locally prohibitive",
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    (REPORT_ROOT / "v3_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest": manifest, "summary": summaries}


def _svg_matrix(path: Path, values: dict[tuple[str, str], float], title: str) -> None:
    cell, left, top = 108, 150, 70
    width, height = left + cell * 4 + 20, top + cell * 4 + 30
    maximum = max([abs(v) for v in values.values()] or [1.0]) or 1.0
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
             '<style>text{font-family:Arial;fill:#222}.title{font-size:17px;font-weight:bold}.small{font-size:12px}</style>',
             f'<text class="title" x="12" y="28">{title}</text>']
    for j, label in enumerate(FAMILIES):
        parts.append(f'<text class="small" text-anchor="middle" x="{left+j*cell+45}" y="52">{label}</text>')
    for i, source in enumerate(FAMILIES):
        y = top + i * cell
        parts.append(f'<text class="small" text-anchor="end" x="{left-8}" y="{y+48}">{source}</text>')
        for j, target in enumerate(FAMILIES):
            x = left + j * cell; value = values.get((source, target), 0.0)
            shade = int(245 - 190 * min(1.0, max(0.0, value / maximum)))
            parts.append(f'<rect x="{x}" y="{y}" width="88" height="88" fill="rgb({shade},{shade},255)"/>')
            parts.append(f'<text class="small" text-anchor="middle" x="{x+44}" y="{y+50}">{value:.3f}</text>')
    parts.append('</svg>'); path.write_text(''.join(parts), encoding='utf-8')


def _v3_gates(summaries: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {r["geometry"]: r for r in summaries}
    h8 = [r for r in rows if r["h"] == 8 and r["policy"] == "natural"]
    diag_component = [float(r["component_accuracy"]) for r in h8
                      if r["geometry"] == "DIAGONAL" and r["source"] == r["target"]]
    baseline_component = [float(r["component_accuracy"]) for r in rows if r["h"] == 0 and r["policy"] == "natural"]
    def add(name: str, passed: bool, value: Any, criterion: str) -> dict[str, Any]:
        return {"gate": name, "status": "PASS" if passed else "FAIL", "value": value, "criterion": criterion}
    return [
        add("A_diagonal_information", by["DIAGONAL"]["D_J"] >= .50, by["DIAGONAL"]["D_J"], ">= 0.50"),
        add("B_global_locality", by["GLOBAL"]["O_J"] / by["GLOBAL"]["D_J"] >= .75 if by["GLOBAL"]["D_J"] else False,
            by["GLOBAL"]["O_J"] / by["GLOBAL"]["D_J"] if by["GLOBAL"]["D_J"] else None, "O/D >= 0.75"),
        add("C_block_locality", by["BLOCK"]["W_J"] / by["BLOCK"]["D_J"] >= .75 if by["BLOCK"]["D_J"] else False,
            by["BLOCK"]["W_J"] / by["BLOCK"]["D_J"] if by["BLOCK"]["D_J"] else None, "W/D >= 0.75 and C <= 0.02"),
        add("C_block_cross", by["BLOCK"]["C_J"] <= .02, by["BLOCK"]["C_J"], "<= 0.02"),
        add("D_diagonal_offdiag", by["DIAGONAL"]["O_J"] <= .02, by["DIAGONAL"]["O_J"], "<= 0.02"),
        add("E_diagonal_learning", all(float(r["D_L_star"]) >= .20 for r in summaries),
            {r["geometry"]: r["D_L_star"] for r in summaries}, "D_L* >= 0.20"),
        add("F_ordered_Q", by["GLOBAL"]["Q_L_star"] < by["BLOCK"]["Q_L_star"] < by["DIAGONAL"]["Q_L_star"] and
            by["BLOCK"]["Q_L_star"] - by["GLOBAL"]["Q_L_star"] >= .05 and by["DIAGONAL"]["Q_L_star"] - by["BLOCK"]["Q_L_star"] >= .05,
            {r["geometry"]: r["Q_L_star"] for r in summaries}, "GLOBAL < BLOCK < DIAGONAL, adjacent gap >= 0.05"),
        add("G_component_sanity", (max(baseline_component or [0]) - min(baseline_component or [0]) <= .10 and
                                    max(diag_component or [0]) - min(diag_component or [0]) <= .10),
            {"baseline": baseline_component, "diag_h8": diag_component}, "within-condition component spread <= 0.10"),
        add("H_independent_zero", abs(by["DIAGONAL"]["O_J"]) <= 1e-10 and by["BLOCK"]["C_J"] <= 1e-10,
            {"diag_O": by["DIAGONAL"]["O_J"], "block_C": by["BLOCK"]["C_J"]}, "analytic independent cells zero"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline ecological information geometry V3")
    parser.add_argument("--run", action="store_true", help="run old audit and V3 Bayes analysis")
    parser.add_argument("--draws", type=int, default=MC_DRAWS)
    args = parser.parse_args()
    if not args.run:
        parser.error("use --run; this module never performs model inference")
    print(json.dumps(write_v3_reports(draws=args.draws), indent=2))


if __name__ == "__main__":
    main()

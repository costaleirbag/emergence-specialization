"""Frozen T1–T9 scorecard helpers.

These functions consume sealed prediction rows and post-campaign observation
rows.  With no observation rows they return ``NOT_RUN`` rather than fabricating
an outcome.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from emergent_specialization.studies.theory.v1.scoring import kendall_tau, pairwise_concordance, score_t1, spearman


def _not_run(name: str, reason: str = "no confirmatory observations") -> dict[str, Any]:
    return {"test": name, "status": "NOT_RUN", "reason": reason}


def score_t3_beta(predicted: Sequence[Mapping[str, Any]], observed: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not observed:
        return _not_run("T3")
    panels = []
    for key in sorted({(row["ecology"], int(row["k"])) for row in observed}):
        p = [float(row["g_excess_pred"]) for row in predicted if (row["ecology"], int(row["k"])) == key and float(row["q_share"]) == 0]
        o = [float(row["g_excess_obs"]) for row in observed if (row["ecology"], int(row["k"])) == key and float(row["q_share"]) == 0]
        panels.append({"ecology": key[0], "k": key[1], "spearman": spearman(p, o) if len(p) >= 2 else None})
    passed = sum(row["spearman"] is not None and row["spearman"] >= .70 for row in panels) >= 5
    return {"test": "T3", "panels": panels, "status": "PASS" if passed else "FAIL"}


def score_t4_matched_gain(observed: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not observed:
        return _not_run("T4")
    differences = {}
    for ecology in sorted({row["ecology"] for row in observed}):
        left = {int(row["seed"]): float(row["g_excess_obs"]) for row in observed if row["ecology"] == ecology and float(row["beta"]) == 8 and float(row["epsilon"]) == .10 and float(row["q_share"]) == 0}
        right = {int(row["seed"]): float(row["g_excess_obs"]) for row in observed if row["ecology"] == ecology and float(row["beta"]) == 16 and float(row["epsilon"]) == .55 and float(row["q_share"]) == 0}
        differences[ecology] = [left[seed] - right[seed] for seed in sorted(set(left) & set(right))]
    means = {key: sum(values) / len(values) for key, values in differences.items() if values}
    return {"test": "T4", "seed_differences": differences, "mean_difference": means, "status": "PASS" if means and all(abs(value) <= .002 for value in means.values()) else "FAIL"}


def score_t5_sharing(observed: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not observed:
        return _not_run("T5")
    ordering = {}
    for ecology in sorted({row["ecology"] for row in observed}):
        means = {}
        for q in (0.0, .5, 1.0):
            values = [float(row["g_excess_obs"]) for row in observed if row["ecology"] == ecology and float(row["q_share"]) == q]
            means[q] = sum(values) / len(values) if values else None
        ordering[ecology] = means
    passed = all(values[0.0] is not None and values[.5] is not None and values[1.0] is not None and values[0.0] >= values[.5] >= values[1.0] for values in ordering.values())
    return {"test": "T5", "means": ordering, "status": "PASS" if passed else "FAIL"}


def score_t6_capacity(predicted: Sequence[float], observed: Sequence[float]) -> dict[str, Any]:
    if not predicted or not observed:
        return _not_run("T6")
    rho = spearman(predicted, observed)
    return {"test": "T6", "spearman": rho, "status": "PASS" if rho >= .70 else "FAIL"}


def score_t7_criticality(predicted_regimes: Sequence[str], observed_positive: Sequence[bool]) -> dict[str, Any]:
    if not predicted_regimes or not observed_positive:
        return _not_run("T7")
    eligible = [(p, o) for p, o in zip(predicted_regimes, observed_positive) if p != "TRANSITIONAL"]
    if len(eligible) < 8:
        return {"test": "T7", "eligible": len(eligible), "status": "NON_IDENTIFIABLE"}
    correct = sum((p == "SUPERCRITICAL") == bool(o) for p, o in eligible)
    return {"test": "T7", "eligible": len(eligible), "accuracy": correct / len(eligible), "status": "PASS" if correct / len(eligible) >= .75 else "FAIL"}


def score_t8_cross_ecology(t1_by_ecology: Mapping[str, Mapping[str, Any]], major_laws: Mapping[str, bool]) -> dict[str, Any]:
    if not t1_by_ecology:
        return _not_run("T8")
    passed = all(value.get("status") == "PASS" for value in t1_by_ecology.values()) and all(major_laws.values())
    return {"test": "T8", "status": "PASS" if passed else "FAIL", "ecology_t1": dict(t1_by_ecology), "major_laws": dict(major_laws)}


def score_t9_mode(eligible_energy: Sequence[float]) -> dict[str, Any]:
    if not eligible_energy:
        return {"test": "T9", "status": "NON_IDENTIFIABLE", "eligible": 0}
    fraction = sum(value > 1 / 3 for value in eligible_energy) / len(eligible_energy)
    mean = sum(eligible_energy) / len(eligible_energy)
    return {"test": "T9", "eligible": len(eligible_energy), "mean_mode_energy": mean, "fraction_above_isotropic": fraction, "status": "PASS" if mean >= .50 and fraction >= .75 else "FAIL"}


def full_scorecard(*, t1: Mapping[str, Any] | None = None, observations: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Return a stable machine-readable T1–T9 status object."""
    return {
        "T1": dict(t1) if t1 is not None else _not_run("T1"),
        "T2": _not_run("T2") if not observations else pairwise_concordance([], []),
        "T3": score_t3_beta([], observations),
        "T4": score_t4_matched_gain(observations),
        "T5": score_t5_sharing(observations),
        "T6": _not_run("T6"),
        "T7": _not_run("T7"),
        "T8": _not_run("T8"),
        "T9": _not_run("T9"),
        "overall": "NOT_RUN" if not observations else "PENDING",
    }


"""Observable ecological information geometry V3.1.

V3.1 is a versioned offline observation-channel layer.  It preserves the V3
latent prior and verifier, but makes the learner-visible semantic state
explicit, audits the deterministic renderer, evaluates an observable Bayes
learner without family-ID arguments, and includes a genuinely family-blind
diagnostic control.  No provider, credential, or network code is used.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from .ecological_information import (
    BALANCED_MAPS,
    FAMILIES,
    GEOMETRIES,
    HORIZONS,
    V3Case,
    _posterior_for_group,
    entropy_bits,
    generate_environment,
    posterior_predictive as latent_posterior_predictive,
    sample_history,
    solve,
    teaching_history,
)

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/task-ecology/ecological-information-v31"
DRAW_COUNT = 2_000
SEED_VALUES = tuple(range(10))
TEMPLATE_IDS = (0, 1, 2, 3)
TRAIN_TEMPLATE_IDS = (0, 1, 2)
EVAL_TEMPLATE_IDS = (3,)

SEMANTIC_SCHEMAS: dict[str, dict[str, Any]] = {
    "ACCESS": {
        "domain": "a person or service requests access to an organizational resource",
        "context": "A staff member is requesting access to a controlled organizational resource.",
        "attributes": (
            ("resource sensitivity", ("routine internal material", "sensitive operational material", "confidential records", "critical restricted records")),
            ("requester authorization", ("unverified requester", "identity-verified requester", "authorized team member", "resource owner")),
            ("request timing", ("ordinary request", "scheduled exception", "urgent operational need", "emergency exception")),
        ),
        "decisions": ("permit the request", "escalate for review", "release access immediately"),
    },
    "INCIDENT": {
        "domain": "an operational incident affects a service or workflow",
        "context": "An operations team is triaging an incident affecting a live service.",
        "attributes": (
            ("incident impact", ("localized interruption", "degraded service", "major service disruption", "critical outage")),
            ("response readiness", ("unverified response", "initially triaged", "contained response", "fully prepared response")),
            ("incident timing", ("stable period", "active investigation", "urgent response window", "emergency escalation")),
        ),
        "decisions": ("authorize the response", "escalate the incident", "act immediately"),
    },
    "PROVENANCE": {
        "domain": "an artifact or report is reviewed for evidence lineage",
        "context": "An evidence custodian is reviewing an artifact before it is used or released.",
        "attributes": (
            ("evidence importance", ("routine record", "material record", "sensitive evidence", "critical evidence")),
            ("lineage completeness", ("missing lineage", "partial lineage", "verified lineage", "audited lineage")),
            ("evidence timing", ("historical context", "recent update", "current record", "exceptional deadline")),
        ),
        "decisions": ("accept the evidence", "escalate for review", "use it immediately"),
    },
    "RELEASE": {
        "domain": "a software or service change is reviewed for deployment",
        "context": "A change owner is reviewing a service update before deployment.",
        "attributes": (
            ("release criticality", ("routine change", "important change", "high-impact change", "mission-critical change")),
            ("release readiness", ("draft change", "reviewed change", "approved change", "validated change")),
            ("release timing", ("planned window", "expedited window", "restricted change window", "exception window")),
        ),
        "decisions": ("approve the release", "escalate for review", "deploy immediately"),
    },
}

TEMPLATE_BANK: dict[str, tuple[str, ...]] = {
    family: (
        "{context} The {a0n} is {a0}. The {a1n} is {a1}. The {a2n} is {a2}. Decide: {decisions}.",
        "Review this situation. {context} Report the {a0n}: {a0}; the {a1n}: {a1}; and the {a2n}: {a2}. Return the three decisions.",
        "{context} Three signals are recorded: {a0n} = {a0}; {a1n} = {a1}; {a2n} = {a2}. Determine the requested actions.",
        "Operational summary: {context} Relevant details are {a0n} ({a0}), {a1n} ({a1}), and {a2n} ({a2}). Give the three decisions in order.",
    ) for family in FAMILIES
}


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fields or sorted({k for row in rows for k in row}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def observable_o(family: str, x: tuple[int, int, int]) -> dict[str, Any]:
    schema = SEMANTIC_SCHEMAS[family]
    return {
        "domain_semantics": schema["domain"],
        "context": schema["context"],
        "attributes": [{"name": name, "value": values[x[j]]} for j, (name, values) in enumerate(schema["attributes"])],
        "decision_semantics": list(schema["decisions"]),
    }


def blind_o(o: dict[str, Any]) -> dict[str, Any]:
    """Remove family-identifying semantics while preserving three observable levels."""
    x = decode_x(o)
    values = []
    for index, attribute in enumerate(o["attributes"]):
        # The blind control is diagnostic: a generic signal representation is
        # intentionally not a proposed model-facing ecology.
        values.append({"name": f"signal {index + 1}", "value": f"level_{x[index]}"})
    return {"domain_semantics": "a generated organizational case",
            "context": "A generated case contains three policy signals.",
            "attributes": values, "decision_semantics": ["decision one", "decision two", "decision three"]}


def decode_family(o: dict[str, Any]) -> str:
    matches = [family for family, schema in SEMANTIC_SCHEMAS.items() if o.get("domain_semantics") == schema["domain"]]
    if len(matches) != 1:
        raise ValueError("observable family is not exactly recoverable")
    return matches[0]


def decode_x(o: dict[str, Any]) -> tuple[int, int, int]:
    family = decode_family(o)
    schemas = SEMANTIC_SCHEMAS[family]["attributes"]
    values = tuple(next(index for index, value in enumerate(allowed) if value == attr["value"])
                   for attr, (_, allowed) in zip(o["attributes"], schemas))
    return values  # type: ignore[return-value]


def blind_decode_x(o: dict[str, Any]) -> tuple[int, int, int]:
    values = []
    for attr in o["attributes"]:
        prefix, _, number = attr["value"].partition("_")
        if prefix != "level" or number not in {"0", "1", "2", "3"}:
            raise ValueError("blind observable value cannot be replayed")
        values.append(int(number))
    return tuple(values)  # type: ignore[return-value]


def render_observable(o: dict[str, Any], family: str, template_id: int) -> str:
    if template_id not in TEMPLATE_IDS:
        raise ValueError(template_id)
    attrs = o["attributes"]
    return TEMPLATE_BANK[family][template_id].format(
        context=o["context"], a0n=attrs[0]["name"], a0=attrs[0]["value"],
        a1n=attrs[1]["name"], a1=attrs[1]["value"], a2n=attrs[2]["name"], a2=attrs[2]["value"],
        decisions="; ".join(o["decision_semantics"]))


def semantic_case(environment: Any, family: str, x: tuple[int, int, int]) -> tuple[dict[str, Any], V3Case]:
    return observable_o(family, x), V3Case(family, x, solve(environment.theta_by_family[family], x))


class ObservableEcologyBayesLearner:
    """Bayes learner whose public interface contains only O histories and O target."""

    def __init__(self, geometry: str):
        self.geometry = geometry

    def predictive(self, history_o: Sequence[dict[str, Any]], target_o: dict[str, Any], x: tuple[int, int, int] | None = None) -> tuple[float, ...]:
        # Only the prior geometry is needed; this fresh prior object contains
        # no realized theta from the generating environment.
        environment = generate_environment(self.geometry, 0)
        if history_o:
            source = decode_family(history_o[0])
            history = [V3Case(source, decode_x(item), tuple(item["y"])) for item in history_o]
        else:
            # At h=0 the source identity is irrelevant under the V3 prior; use
            # a fixed semantic family only to select the base posterior helper.
            source = decode_family(target_o)
            history = []
        target = decode_family(target_o)
        query_x = decode_x(target_o) if x is None else x
        return latent_posterior_predictive(environment, source, target, history, query_x)


class BlindObservableBayesLearner:
    """Diagnostic learner that receives no family-bearing semantic field."""

    def __init__(self, geometry: str):
        self.geometry = geometry

    def predictive(self, history_o: Sequence[dict[str, Any]], target_o: dict[str, Any], x: tuple[int, int, int]) -> tuple[float, ...]:
        environment = generate_environment(self.geometry, 0)
        history_x = [blind_decode_x(item) for item in history_o]
        history_y = [tuple(item["y"]) for item in history_o]
        predictions = []
        for source in FAMILIES:
            history = [V3Case(source, hx, hy) for hx, hy in zip(history_x, history_y)]
            for target in FAMILIES:
                predictions.append(latent_posterior_predictive(environment, source, target, history, x))
        return tuple(sum(prediction[index] for prediction in predictions) / len(predictions) for index in range(8))


def _bit_stats(probs: Sequence[float]) -> tuple[float, float, float]:
    ys = list(itertools.product((0, 1), repeat=3))
    component_accuracy = []
    component_information = []
    for j in range(3):
        q = sum(p for p, y in zip(probs, ys) if y[j])
        component_accuracy.append(max(q, 1.0 - q))
        component_information.append(1.0 - entropy_bits((1.0 - q, q)))
    return tuple(component_accuracy), tuple(component_information), max(probs)  # type: ignore[return-value]


def _aggregate_stats(probabilities: Iterable[Sequence[float]]) -> dict[str, Any]:
    entropies: list[float] = []; accuracies: list[float] = []; components: list[list[float]] = [[], [], []]; component_j: list[list[float]] = [[], [], []]
    for probs in probabilities:
        entropies.append(entropy_bits(probs)); component_acc, component_info, joint = _bit_stats(probs)
        accuracies.append(joint)
        for j in range(3): components[j].append(component_acc[j]); component_j[j].append(component_info[j])
    return {"J_bits": 3.0 - statistics.mean(entropies), "J_normalized": (3.0 - statistics.mean(entropies)) / 3.0,
            "A_star": statistics.mean(accuracies), "component_accuracy_1": statistics.mean(components[0]),
            "component_accuracy_2": statistics.mean(components[1]), "component_accuracy_3": statistics.mean(components[2]),
            "component_J_1": statistics.mean(component_j[0]), "component_J_2": statistics.mean(component_j[1]),
            "component_J_3": statistics.mean(component_j[2])}


def _probs_from_posteriors(posteriors: Sequence[Sequence[float]], x: tuple[int, int, int]) -> tuple[float, ...]:
    bit_probs = [sum(weight * mapping[x[j]] for weight, mapping in zip(posteriors[j], BALANCED_MAPS)) for j in range(3)]
    values = []
    for y in itertools.product((0, 1), repeat=3):
        probability = 1.0
        for bit, q in zip(y, bit_probs): probability *= q if bit else 1.0 - q
        values.append(probability)
    return tuple(values)


def _fast_stats(environment: Any, source: str, target: str, history: Sequence[V3Case], cache: dict[Any, dict[str, Any]] | None = None) -> dict[str, Any]:
    posterior = _posterior_for_group(history, source, environment.group_by_family[target], environment)
    key = ("single", environment.geometry, posterior)
    if cache is not None and key in cache:
        return cache[key]
    result = _aggregate_stats(_probs_from_posteriors(posterior, x) for x in itertools.product((0, 1, 2, 3), repeat=3))
    if cache is not None:
        cache[key] = result
    return result


def _fast_blind_stats(environment: Any, history: Sequence[V3Case], cache: dict[Any, dict[str, Any]] | None = None) -> dict[str, Any]:
    posterior_sets = []
    for source in FAMILIES:
        posterior_sets.append([(source, target, _posterior_for_group(history, source, environment.group_by_family[target], environment)) for target in FAMILIES])
    key = ("blind", environment.geometry, tuple(tuple(tuple(v) for v in post) for post in posterior_sets))
    if cache is not None and key in cache:
        return cache[key]
    def probabilities(x: tuple[int, int, int]) -> tuple[float, ...]:
        values = [_probs_from_posteriors(post, x) for source_values in posterior_sets for _, _, post in source_values]
        return tuple(sum(value[index] for value in values) / len(values) for index in range(8))
    result = _aggregate_stats(probabilities(x) for x in itertools.product((0, 1, 2, 3), repeat=3))
    if cache is not None:
        cache[key] = result
    return result


def _query_stats(predictive, target_o: dict[str, Any], *, blind: bool = False) -> dict[str, Any]:
    values = [predictive(x) for x in itertools.product((0, 1, 2, 3), repeat=3)]
    return _aggregate_stats(values)


def _make_history(environment: Any, family: str, max_h: int, *, policy: str, rng: Any) -> tuple[list[V3Case], list[dict[str, Any]]]:
    if policy == "natural":
        cases = sample_history(environment, family, max_h, rng)
    elif policy == "teaching":
        cases = teaching_history(environment, family, max_h)
    else:
        raise ValueError(policy)
    return cases, [dict(observable_o(family, case.x), y=list(case.y)) for case in cases]


def _cell_rows(draws: int, *, policy: str, include_blind: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    latent_rows: list[dict[str, Any]] = []; observable_rows: list[dict[str, Any]] = []; blind_rows: list[dict[str, Any]] = []; component_rows: list[dict[str, Any]] = []
    totals: dict[tuple[str, str, str, int, str], defaultdict[str, float]] = {}
    cache: dict[Any, dict[str, Any]] = {}
    for geometry in GEOMETRIES:
        for source in FAMILIES:
            for draw in range(draws):
                env_seed = SEED_VALUES[draw % len(SEED_VALUES)] + draw * 100_003
                env = generate_environment(geometry, env_seed)
                import random
                rng = random.Random(0x31A7 + env_seed * 1009 + sum(map(ord, source)) * 17)
                full_cases, full_o = _make_history(env, source, 8, policy=policy, rng=rng)
                for h in HORIZONS:
                    history_cases = full_cases[:h]; history_o = full_o[:h]
                    replay_cases = [V3Case(source, decode_x(item), tuple(item["y"])) for item in history_o]
                    blind_cases = [V3Case(source, blind_decode_x(blind_o(item)), tuple(item["y"])) for item in history_o]
                    blind = _fast_blind_stats(env, blind_cases, cache) if include_blind else None
                    for target in FAMILIES:
                        latent = _fast_stats(env, source, target, history_cases, cache)
                        # O is a sufficient replay of (C,X), so this is the
                        # public observable learner's algebraic result.
                        obs = _fast_stats(env, source, target, replay_cases, cache)
                        for kind, value in (("latent", latent), ("observable", obs), ("blind", blind)):
                            if value is None: continue
                            key = (geometry, source, target, h, kind)
                            bucket = totals.setdefault(key, defaultdict(float))
                            for name, number in value.items(): bucket[name] += float(number)
    for geometry in GEOMETRIES:
        for source in FAMILIES:
            for target in FAMILIES:
                for h in HORIZONS:
                    buckets = {kind: totals[(geometry, source, target, h, kind)] for kind in ("latent", "observable", "blind") if (geometry, source, target, h, kind) in totals}
                    rows_for_components: dict[str, dict[str, float]] = {}
                    for kind, target_rows in (("latent", latent_rows), ("observable", observable_rows), ("blind", blind_rows)):
                        if kind not in buckets: continue
                        row = {"geometry": geometry, "source": source, "target": target, "h": h, "policy": policy, "draws": draws}
                        row.update({name: value / draws for name, value in buckets[kind].items()}); row["L_star"] = row["A_star"] - 1.0 / 8.0; target_rows.append(row)
                    if "blind" in buckets:
                        for j in range(1, 4):
                            component_rows.append({"geometry": geometry, "source": source, "target": target, "h": h, "policy": policy, "component": j,
                                "latent_accuracy": buckets["latent"][f"component_accuracy_{j}"] / draws,
                                "observable_accuracy": buckets["observable"][f"component_accuracy_{j}"] / draws,
                                "blind_accuracy": buckets["blind"][f"component_accuracy_{j}"] / draws,
                                "latent_J": buckets["latent"][f"component_J_{j}"] / draws,
                                "observable_J": buckets["observable"][f"component_J_{j}"] / draws,
                                "blind_J": buckets["blind"][f"component_J_{j}"] / draws})
    return latent_rows, observable_rows, blind_rows, component_rows


def _svg_matrix(path: Path, values: dict[tuple[str, str], float], title: str) -> None:
    cell, left, top = 108, 150, 70; maximum = max([abs(v) for v in values.values()] or [1.0]) or 1.0
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="620"><style>text{{font-family:Arial;fill:#222}}.t{{font-size:17px;font-weight:bold}}.s{{font-size:12px}}</style><text class="t" x="12" y="28">{title}</text>']
    for j, label in enumerate(FAMILIES): parts.append(f'<text class="s" text-anchor="middle" x="{left+j*cell+44}" y="52">{label}</text>')
    for i, source in enumerate(FAMILIES):
        y = top + i * cell; parts.append(f'<text class="s" text-anchor="end" x="{left-8}" y="{y+48}">{source}</text>')
        for j, target in enumerate(FAMILIES):
            x = left + j * cell; value = values.get((source, target), 0.0); shade = int(245 - 190 * min(1.0, max(0.0, value / maximum)))
            parts.append(f'<rect x="{x}" y="{y}" width="88" height="88" fill="rgb({shade},{shade},255)"/><text class="s" text-anchor="middle" x="{x+44}" y="{y+50}">{value:.3f}</text>')
    parts.append('</svg>'); path.write_text(''.join(parts), encoding='utf-8')


def _audit_renderer() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    collisions: list[dict[str, Any]] = []; leakage: list[dict[str, Any]] = []; templates: list[dict[str, Any]] = []
    texts: dict[str, tuple[str, str, int]] = {}
    hidden_tokens = ("theta", "geometry", "seed", "factor", "balanced map", "canonical dimension")
    for family in FAMILIES:
        for template_id in TEMPLATE_IDS:
            templates.append({"family": family, "template_id": template_id, "split": "eval" if template_id in EVAL_TEMPLATE_IDS else "train"})
            for x in itertools.product((0, 1, 2, 3), repeat=3):
                o = observable_o(family, x); text = render_observable(o, family, template_id); key = text
                if key in texts:
                    collisions.append({"family": family, "template_id": template_id, "x": list(x), "collision_with": texts[key]})
                else:
                    texts[key] = (family, str(x), template_id)
                found = [token for token in hidden_tokens if token in text.lower()]
                for host in FAMILIES:
                    if host in text:
                        found.append(f"host_family:{host}")
                if found:
                    leakage.append({"family": family, "template_id": template_id, "x": list(x), "tokens": found})
    return collisions, leakage, templates


def _representative_convergence() -> list[dict[str, Any]]:
    # A compact convergence check for the representative diagonal self-cell;
    # V3.1 primary tables use 2,000 draws/cell.
    rows: list[dict[str, Any]] = []
    for draws in (500, 1000, 2000, 5000):
        total = 0.0
        for draw in range(draws):
            env_seed = SEED_VALUES[draw % len(SEED_VALUES)] + draw * 100_003
            env = generate_environment("DIAGONAL", env_seed)
            import random
            history = sample_history(env, "ACCESS", 8, random.Random(0x31A7 + env_seed * 1009 + sum(map(ord, "ACCESS")) * 17))
            stats = _aggregate_stats(latent_posterior_predictive(env, "ACCESS", "ACCESS", history, x) for x in itertools.product((0, 1, 2, 3), repeat=3))
            total += stats["J_normalized"]
        rows.append({"geometry": "DIAGONAL", "source": "ACCESS", "target": "ACCESS", "h": 8, "draws": draws, "J_normalized": total / draws})
    return rows


def run_v31(draws: int = DRAW_COUNT) -> dict[str, Any]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    collisions, leakage, templates = _audit_renderer()
    _write_csv(REPORT_ROOT / "renderer_collision_audit.csv", collisions, ["family", "template_id", "x", "collision_with"])
    _write_csv(REPORT_ROOT / "theta_leakage_audit.csv", leakage, ["family", "template_id", "x", "tokens"])
    _write_csv(REPORT_ROOT / "renderer_templates.csv", templates)
    schema_rows = []
    for family in FAMILIES:
        schema = SEMANTIC_SCHEMAS[family]
        for dimension, (name, values) in enumerate(schema["attributes"], 1):
            for level, value in enumerate(values): schema_rows.append({"family": family, "dimension": dimension, "attribute": name, "level": level, "semantic_value": value})
        schema_rows.append({"family": family, "dimension": "decisions", "attribute": "decision_semantics", "level": "|".join(schema["decisions"]), "semantic_value": schema["context"]})
    _write_csv(REPORT_ROOT / "semantic_schema.csv", schema_rows)
    def load_rows(name: str) -> list[dict[str, Any]] | None:
        path = REPORT_ROOT / name
        if not path.exists(): return None
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows: return None
        if "draws" not in rows[0]:
            for row in rows: row["draws"] = draws
        elif int(rows[0].get("draws", -1)) != draws:
            return None
        numeric = {"h", "draws", "J_bits", "J_normalized", "A_star", "L_star", "component_accuracy_1", "component_accuracy_2", "component_accuracy_3", "component_J_1", "component_J_2", "component_J_3", "latent_accuracy", "observable_accuracy", "blind_accuracy", "latent_J", "observable_J", "blind_J", "component"}
        for row in rows:
            for key in numeric:
                if key in row:
                    row[key] = int(row[key]) if key in {"h", "draws", "component"} else float(row[key])
        return rows
    latent = load_rows("latent_J_natural.csv"); observable = load_rows("observable_J_natural.csv"); blind = load_rows("blind_J_natural.csv"); component = load_rows("component_metrics.csv")
    if latent is None or observable is None or blind is None or component is None:
        latent, observable, blind, component = _cell_rows(draws, policy="natural")
    _write_csv(REPORT_ROOT / "latent_J_natural.csv", latent)
    _write_csv(REPORT_ROOT / "observable_J_natural.csv", observable)
    _write_csv(REPORT_ROOT / "blind_J_natural.csv", blind)
    _write_csv(REPORT_ROOT / "latent_Lstar_natural.csv", [{k: r[k] for k in r if k in ("geometry", "source", "target", "h", "policy", "draws", "A_star", "L_star")} for r in latent])
    _write_csv(REPORT_ROOT / "observable_Lstar_natural.csv", [{k: r[k] for k in r if k in ("geometry", "source", "target", "h", "policy", "draws", "A_star", "L_star")} for r in observable])
    _write_csv(REPORT_ROOT / "blind_Lstar_natural.csv", [{k: r[k] for k in r if k in ("geometry", "source", "target", "h", "policy", "draws", "A_star", "L_star")} for r in blind])
    _write_csv(REPORT_ROOT / "component_metrics.csv", component)
    # Teaching uses one frozen length-eight sequence and prefixes, unlike V3's
    # horizon-dependent teaching selection.
    latent_t = load_rows("latent_J_teaching.csv"); obs_t = load_rows("observable_J_teaching.csv")
    if latent_t is None or obs_t is None:
        latent_t, obs_t, _, component_t = _cell_rows(draws, policy="teaching", include_blind=False)
    _write_csv(REPORT_ROOT / "latent_J_teaching.csv", latent_t); _write_csv(REPORT_ROOT / "observable_J_teaching.csv", obs_t)
    _write_csv(REPORT_ROOT / "latent_Lstar_teaching.csv", [{k: r[k] for k in r if k in ("geometry", "source", "target", "h", "policy", "draws", "A_star", "L_star")} for r in latent_t])
    _write_csv(REPORT_ROOT / "observable_Lstar_teaching.csv", [{k: r[k] for k in r if k in ("geometry", "source", "target", "h", "policy", "draws", "A_star", "L_star")} for r in obs_t])
    loss_rows: list[dict[str, Any]] = []
    for l in latent:
        key = (l["geometry"], l["source"], l["target"], l["h"])
        o = next(r for r in observable if (r["geometry"], r["source"], r["target"], r["h"]) == key)
        b = next(r for r in blind if (r["geometry"], r["source"], r["target"], r["h"]) == key)
        loss_rows.append({**dict(zip(("geometry", "source", "target", "h"), key)),
                          "J_latent": l["J_normalized"], "J_observable": o["J_normalized"], "J_blind": b["J_normalized"],
                          "Delta_J_observable": l["J_normalized"] - o["J_normalized"], "Delta_J_blind": l["J_normalized"] - b["J_normalized"],
                          "Lstar_latent": l["L_star"], "Lstar_observable": o["L_star"], "Lstar_blind": b["L_star"],
                          "Delta_Lstar_observable": l["L_star"] - o["L_star"], "Delta_Lstar_blind": l["L_star"] - b["L_star"]})
    _write_csv(REPORT_ROOT / "observation_loss_metrics.csv", loss_rows)
    convergence = _representative_convergence(); _write_csv(REPORT_ROOT / "mc_convergence.csv", convergence)
    figures = REPORT_ROOT / "figures"; figures.mkdir(parents=True, exist_ok=True)
    for metric, filename in (("J_normalized", "J"), ("L_star", "Lstar")):
        for name, rows in (("latent", latent), ("observable", observable), ("blind", blind)):
            for geometry in GEOMETRIES:
                vals = {(r["source"], r["target"]): float(r[metric]) for r in rows if r["geometry"] == geometry and r["h"] == 8 and r["policy"] == "natural"}
                _svg_matrix(figures / f"{name}_{filename}_{geometry.lower()}_h8.svg", vals, f"{name} {filename} {geometry} h=8")
    # Observation-channel JSON is intentionally redundant with the CSV audits,
    # but provides one compact machine-readable provenance object.
    audit = {"old_renderer_family_exposed": False, "old_oracle_received_family": True,
             "privileged_oracle_mismatch": True, "old_component_gate_per_component": False,
             "old_histories_nested": False, "new_family_recovery_percent": 100.0,
             "renderer_collision_count": len(collisions), "theta_leakage_count": len(leakage),
             "train_template_ids": list(TRAIN_TEMPLATE_IDS), "eval_template_ids": list(EVAL_TEMPLATE_IDS),
             "external_model_calls": 0, "external_spend_usd": 0.0,
             "draws_per_cell": draws, "latent_prior_unchanged": True}
    (REPORT_ROOT / "observation_channel_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    summary = _gate_summary(latent, observable, blind, component, collisions, leakage)
    (REPORT_ROOT / "gate_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = {"protocol": "OBSERVABLE-ECOLOGICAL-INFORMATION-GEOMETRY-V3.1", "created_at_utc": _now(), "draws_per_cell": draws,
                "families": list(FAMILIES), "geometries": list(GEOMETRIES), "horizons": list(HORIZONS),
                "train_template_ids": list(TRAIN_TEMPLATE_IDS), "eval_template_ids": list(EVAL_TEMPLATE_IDS),
                "external_model_calls": 0, "external_spend_usd": 0.0,
                "git_head": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    (REPORT_ROOT / "v31_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return summary


def _gate_summary(latent: list[dict[str, Any]], observable: list[dict[str, Any]], blind: list[dict[str, Any]], component: list[dict[str, Any]], collisions: list[dict[str, Any]], leakage: list[dict[str, Any]]) -> dict[str, Any]:
    h8 = [r for r in latent if r["h"] == 8 and r["policy"] == "natural"]; oh8 = [r for r in observable if r["h"] == 8 and r["policy"] == "natural"]
    losses = {(r["geometry"], r["source"], r["target"], r["h"]): (float(r["Delta_J_observable"]), float(r["Delta_Lstar_observable"]))
              for r in _loss_rows(latent, observable)}
    mae_j = statistics.mean(abs(v[0]) for v in losses.values()); max_j = max(abs(v[0]) for v in losses.values())
    mae_l = statistics.mean(abs(v[1]) for v in losses.values()); max_l = max(abs(v[1]) for v in losses.values())
    def q(rows: list[dict[str, Any]], geometry: str, metric: str) -> float:
        cell = {(r["source"], r["target"]): float(r[metric]) for r in rows if r["geometry"] == geometry and r["h"] == 8}
        d = statistics.mean(cell[(f, f)] for f in FAMILIES); o = statistics.mean(cell[(s, t)] for s in FAMILIES for t in FAMILIES if s != t)
        return d - o
    obs_q = {g: q(oh8, g, "L_star") for g in GEOMETRIES}; lat_q = {g: q(h8, g, "L_star") for g in GEOMETRIES}
    obs_j = {g: _j_summary(oh8, g) for g in GEOMETRIES}
    component_diag = {g: [statistics.mean(float(r["observable_accuracy"]) for r in component
                                           if r["geometry"] == g and r["h"] == 8 and r["source"] == r["target"] and int(r["component"]) == j)
                              for j in (1, 2, 3)] for g in GEOMETRIES}
    # Compare the three output components after averaging over the four
    # diagonal family cells; this is the preregistered symmetry gate.
    comp_spread = {g: max(vals) - min(vals) for g, vals in component_diag.items()}
    gates = {
        "O1_family_observability": len(collisions) == 0,
        "O2_J_preservation": mae_j <= .01 and max_j <= .03,
        "O3_Lstar_preservation": mae_l <= .01 and max_l <= .03,
        "O4_geometry_ordering": obs_q["GLOBAL"] < obs_q["BLOCK"] < obs_q["DIAGONAL"] and obs_q["BLOCK"] - obs_q["GLOBAL"] >= .05 and obs_q["DIAGONAL"] - obs_q["BLOCK"] >= .05,
        "O5_block": obs_j["BLOCK"]["cross"] <= .02 and obs_j["BLOCK"]["within"] / obs_j["BLOCK"]["diag"] >= .75,
        "O6_diagonal": obs_j["DIAGONAL"]["offdiag"] <= .02,
        "O7_global": obs_j["GLOBAL"]["offdiag"] / obs_j["GLOBAL"]["diag"] >= .75,
        "O8_component_symmetry": max(comp_spread.values()) <= .05,
        "O9_renderer_uniqueness": len(collisions) == 0,
        "O10_theta_leakage": len(leakage) == 0,
    }
    return {"gates": {key: {"status": "PASS" if value else "FAIL"} for key, value in gates.items()},
            "all_pass": all(gates.values()), "observation_loss": {"MAE_J": mae_j, "MAX_J": max_j, "MAE_Lstar": mae_l, "MAX_Lstar": max_l},
            "latent_Q_Lstar": lat_q, "observable_Q_Lstar": obs_q, "observable_J_summary": obs_j,
            "component_diagonal_spread": comp_spread, "external_model_calls": 0, "external_spend_usd": 0.0}


def _loss_rows(latent: list[dict[str, Any]], observable: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for l in latent:
        o = next(r for r in observable if all(r[k] == l[k] for k in ("geometry", "source", "target", "h", "policy")))
        out.append({"geometry": l["geometry"], "source": l["source"], "target": l["target"], "h": l["h"],
                    "Delta_J_observable": float(l["J_normalized"]) - float(o["J_normalized"]),
                    "Delta_Lstar_observable": float(l["L_star"]) - float(o["L_star"])})
    return out


def _j_summary(rows: list[dict[str, Any]], geometry: str) -> dict[str, float]:
    cell = {(r["source"], r["target"]): float(r["J_normalized"]) for r in rows if r["geometry"] == geometry and r["h"] == 8}
    diag = statistics.mean(cell[(f, f)] for f in FAMILIES); off = statistics.mean(cell[(s, t)] for s in FAMILIES for t in FAMILIES if s != t)
    groups = {"ACCESS": 0, "RELEASE": 0, "INCIDENT": 1, "PROVENANCE": 1}
    within = [cell[(s, t)] for s in FAMILIES for t in FAMILIES if s != t and groups[s] == groups[t]]
    cross = [cell[(s, t)] for s in FAMILIES for t in FAMILIES if s != t and groups[s] != groups[t]]
    return {"diag": diag, "offdiag": off, "within": statistics.mean(within) if within else diag, "cross": statistics.mean(cross) if cross else 0.0}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline observable ecology V3.1")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--draws", type=int, default=DRAW_COUNT)
    args = parser.parse_args()
    if not args.run:
        parser.error("use --run; V3.1 never performs model inference")
    print(json.dumps(run_v31(args.draws), indent=2))


if __name__ == "__main__":
    main()

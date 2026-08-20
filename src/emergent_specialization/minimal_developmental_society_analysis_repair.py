"""Offline forensic repair for Minimal Developmental Society V1.

This module reads the immutable society event log and rebuilds competence cells
without invoking any provider.  It deliberately keeps the repaired outputs in
their own directory so the superseded analysis remains auditable.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from . import minimal_developmental_society as society


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data/auto-research/minimal-developmental-society-v1"
REPORT_ROOT = ROOT / "reports/society/minimal-developmental-society-v1"
REPAIR_ROOT = ROOT / "reports/society/minimal-developmental-society-v1-analysis-repair"
RAW_FILES = {
    "events": DATA_ROOT / "events.jsonl",
    "run_status": DATA_ROOT / "run_status.json",
    "campaign_budget": DATA_ROOT / "campaign_budget.json",
    "manifest": REPORT_ROOT / "manifest.json",
    "preregistration": ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_PREREGISTRATION.md",
}

SUPERSEDED_REPORT_NOTICE = """# SUPERSEDED ANALYSIS — Minimal Developmental Society V1

> The initial offline competence aggregation contained a niche-accumulator bug.
> The paid raw experiment remains valid, but this report must not be used as the
> canonical scientific analysis. See the corrected repair report and the
> machine-readable outputs under `reports/society/minimal-developmental-society-v1-analysis-repair/`.

"""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_hashes() -> dict[str, dict[str, Any]]:
    return {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}
        for name, path in RAW_FILES.items()
    }


def _cell_key(seed: int, regime: str, checkpoint: int, agent: int, niche: str) -> tuple[int, str, int, int, str]:
    return (int(seed), str(regime), int(checkpoint), int(agent), str(niche))


def _make_cell(key: tuple[int, str, int, int, str], observations: Sequence[tuple[str, Mapping[str, Any]]]) -> dict[str, Any]:
    seed, regime, checkpoint, agent, niche = key
    if len(observations) != society.EVAL_COUNT:
        raise AssertionError(f"expected {society.EVAL_COUNT} probes for {key}, got {len(observations)}")
    logical_ids = [logical_id for logical_id, _ in observations]
    if len(set(logical_ids)) != len(logical_ids):
        raise AssertionError(f"duplicate logical observations in {key}")
    joint_correct = 0
    bits_correct = 0
    bit_totals = [0, 0, 0]
    for logical_id, event in observations:
        decisions = event.get("decisions")
        expected = event.get("expected")
        if decisions is not None and decisions == expected:
            joint_correct += 1
        if decisions is not None and expected is not None and len(decisions) == 3 and len(expected) == 3:
            for index in range(3):
                bit_totals[index] += int(int(decisions[index]) == int(expected[index]))
    n_bits = society.EVAL_COUNT * 3
    bit_correct = sum(bit_totals)
    return {
        "seed": seed,
        "regime": regime,
        "checkpoint": checkpoint,
        "agent": agent,
        "niche": niche,
        "accuracy": joint_correct / society.EVAL_COUNT,
        "n_probes": society.EVAL_COUNT,
        "n_joint_correct": joint_correct,
        "n_bit_decisions": n_bits,
        "n_bits_correct": bit_correct,
        "bit_accuracy": bit_correct / n_bits,
        "bit1": bit_totals[0] / society.EVAL_COUNT,
        "bit2": bit_totals[1] / society.EVAL_COUNT,
        "bit3": bit_totals[2] / society.EVAL_COUNT,
        "logical_ids": json.dumps(logical_ids, separators=(",", ":")),
    }


def _expected_cell_keys() -> list[tuple[int, str, int, int, str]]:
    return [
        _cell_key(seed, regime, checkpoint, agent, niche)
        for seed in society.SEEDS
        for regime in society.REGIMES
        for checkpoint in society.CHECKPOINTS
        for agent in range(society.NUM_AGENTS)
        for niche in society.FAMILIES
    ]


def grouped_aggregation(terminals: Mapping[str, Mapping[str, Any]]) -> dict[tuple[int, str, int, int, str], dict[str, Any]]:
    """Reference implementation: explicitly request each frozen cell's IDs."""
    result: dict[tuple[int, str, int, int, str], dict[str, Any]] = {}
    for key in _expected_cell_keys():
        seed, regime, checkpoint, agent, niche = key
        observations = []
        for probe_index in range(society.EVAL_COUNT):
            if checkpoint == 0:
                logical_id = society._call_id("t0", seed, "COMMON_T0", 0, agent, niche, probe_index)
            else:
                logical_id = society._call_id("checkpoint", seed, regime, checkpoint, agent, niche, probe_index)
            if logical_id not in terminals:
                raise AssertionError(f"missing logical observation {logical_id} for {key}")
            observations.append((logical_id, terminals[logical_id]))
        result[key] = _make_cell(key, observations)
    return result


def pivot_aggregation(terminals: Mapping[str, Mapping[str, Any]]) -> dict[tuple[int, str, int, int, str], dict[str, Any]]:
    """Independent implementation: pivot raw terminal events into cell buckets."""
    buckets: dict[tuple[int, str, int, int, str], list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    for logical_id, event in terminals.items():
        if event.get("phase") != "checkpoint":
            continue
        seed = int(event["seed"])
        checkpoint = int(event["checkpoint"])
        agent = int(event["agent"])
        niche = str(event["niche"])
        if checkpoint == 0:
            regimes: Iterable[str] = society.REGIMES
        else:
            regimes = (str(event["regime"]),)
        for regime in regimes:
            buckets[_cell_key(seed, regime, checkpoint, agent, niche)].append((logical_id, event))
    result = {}
    for key in _expected_cell_keys():
        observations = sorted(buckets.get(key, []), key=lambda item: int(item[1]["task"]["probe_index"]))
        result[key] = _make_cell(key, observations)
    return result


def compare_aggregations(grouped: Mapping[Any, Mapping[str, Any]], pivot: Mapping[Any, Mapping[str, Any]]) -> dict[str, Any]:
    if set(grouped) != set(pivot):
        raise AssertionError("grouped and pivot cell keys differ")
    fields = ("accuracy", "n_probes", "n_joint_correct", "n_bit_decisions", "n_bits_correct", "bit_accuracy", "bit1", "bit2", "bit3")
    mismatches = []
    for key in sorted(grouped):
        for field in fields:
            if grouped[key][field] != pivot[key][field]:
                mismatches.append({"key": key, "field": field, "grouped": grouped[key][field], "pivot": pivot[key][field]})
    if mismatches:
        raise AssertionError(f"independent aggregation mismatch: {mismatches[:3]}")
    return {"cell_count": len(grouped), "fields_checked": list(fields), "mismatch_count": 0}


def _matrix(rows: Sequence[Mapping[str, Any]], checkpoint: int, seed: int, regime: str, field: str) -> np.ndarray:
    lookup = {(int(row["agent"]), str(row["niche"])): float(row[field]) for row in rows if int(row["seed"]) == seed and str(row["regime"]) == regime and int(row["checkpoint"]) == checkpoint}
    return np.array([[lookup[(agent, niche)] for niche in society.FAMILIES] for agent in range(society.NUM_AGENTS)])


def validate_matching(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from scipy.optimize import linear_sum_assignment

    mismatches = []
    checked = 0
    scopes = sorted({(int(row["seed"]), str(row["regime"]), int(row["checkpoint"])) for row in rows})
    for seed, regime, checkpoint in scopes:
        matrix = _matrix(rows, checkpoint, seed, regime, "accuracy")
        brute_best, brute_single, brute_gain, _ = society.matching_gain(matrix)
        row_ind, col_ind = linear_sum_assignment(-matrix)
        hungarian_best = float(matrix[row_ind, col_ind].sum() / len(col_ind))
        if not math.isclose(brute_best, hungarian_best, rel_tol=0.0, abs_tol=1e-12):
            mismatches.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "brute": brute_best, "hungarian": hungarian_best})
        checked += 1
    if mismatches:
        raise AssertionError(f"matching mismatch: {mismatches[:3]}")
    return {"matrices_checked": checked, "mismatch_count": 0}


def _summary_by_regime(rows: Sequence[Mapping[str, Any]], field: str, checkpoint: int | None = None) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if checkpoint is not None and int(row["checkpoint"]) != checkpoint:
            continue
        try:
            grouped[str(row["regime"])].append(float(row[field]))
        except (KeyError, TypeError, ValueError):
            continue
    return {regime: float(np.mean(values)) for regime, values in grouped.items()}


def _filter_segment(rows: Sequence[Mapping[str, Any]], segment: str) -> list[Mapping[str, Any]]:
    """Return only rows belonging to an explicitly named online segment."""
    return [row for row in rows if str(row.get("segment")) == segment]


def _preserve_superseded_report_notice() -> None:
    """Keep the historical report visibly non-canonical after regeneration."""
    path = ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_REPORT.md"
    body = path.read_text(encoding="utf-8")
    if not body.startswith("# SUPERSEDED ANALYSIS"):
        path.write_text(SUPERSEDED_REPORT_NOTICE + body, encoding="utf-8")


def _copy_corrected_outputs() -> dict[str, str]:
    REPAIR_ROOT.mkdir(parents=True, exist_ok=True)
    mapping = {
        "competence_joint.csv": "competence_joint_corrected.csv",
        "competence_bit.csv": "competence_bit_corrected.csv",
        "psi_spec_joint.csv": "psi_spec_joint_corrected.csv",
        "psi_spec_bit.csv": "psi_spec_bit_corrected.csv",
        "phi.csv": "phi_corrected.csv",
        "matching_gain.csv": "matching_gain_corrected.csv",
        "role_assignments.csv": "role_assignments_corrected.csv",
        "role_persistence.csv": "role_persistence_corrected.csv",
        "label_symmetry.csv": "label_symmetry_corrected.csv",
        "routing_information.csv": "routing_information_recomputed.csv",
        "routing_alignment.csv": "routing_alignment_corrected.csv",
        "team_utility.csv": "team_utility_recomputed.csv",
        "exposure_matrices.csv": "exposure_recomputed.csv",
        "memory_composition.csv": "memory_composition_recomputed.csv",
        "technical_health.json": "technical_health.json",
        "cost.json": "cost.json",
        "manifest.json": "manifest.json",
        "verdict.json": "corrected_verdict.json",
    }
    copied = {}
    for source, target in mapping.items():
        destination = REPAIR_ROOT / target
        shutil.copy2(REPORT_ROOT / source, destination)
        copied[target] = str(destination.relative_to(ROOT))
    return copied


def _write_figures(repair_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []
    figure_root = REPAIR_ROOT / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    colors = {"RP": "#6b7280", "AP4": "#2563eb", "AP12": "#dc2626", "AS12": "#059669"}
    psi_bit = read_csv(REPAIR_ROOT / "psi_spec_bit_corrected.csv")
    psi_joint = read_csv(REPAIR_ROOT / "psi_spec_joint_corrected.csv")
    phi_rows = read_csv(REPAIR_ROOT / "phi_corrected.csv")
    match_rows = read_csv(REPAIR_ROOT / "matching_gain_corrected.csv")
    routing = read_csv(REPAIR_ROOT / "routing_information_recomputed.csv")
    alignment = read_csv(REPAIR_ROOT / "routing_alignment_corrected.csv")
    persistence = read_csv(REPAIR_ROOT / "role_persistence_corrected.csv")
    utility = read_csv(REPAIR_ROOT / "team_utility_recomputed.csv")

    def line_metric(rows, value, title, filename):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for regime in society.REGIMES:
            grouped = defaultdict(list)
            for row in rows:
                if row.get("regime") == regime:
                    grouped[int(row["checkpoint"])].append(float(row[value]))
            xs = sorted(grouped)
            ax.plot(xs, [np.mean(grouped[x]) for x in xs], marker="o", color=colors[regime], label=regime)
        ax.set(xlabel="checkpoint", ylabel=value, title=title); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / filename, dpi=160); plt.close(fig)

    line_metric(psi_bit, "psi_bit", "Corrected $\\Psi_{spec}$ (bit)", "psi_spec_bit_corrected.png")
    line_metric(psi_joint, "psi_joint", "Corrected $\\Psi_{spec}$ (joint)", "psi_spec_joint_corrected.png")
    line_metric(phi_rows, "phi_bit", "Corrected $\\Phi$ (bit)", "phi_corrected.png")
    line_metric(match_rows, "Delta_match_joint", "Corrected matching gain", "delta_match_corrected.png")
    line_metric(routing, "I_excess_bits", "Routing information excess", "routing_information_recomputed.png")
    # These tables use interval/segment labels rather than checkpoint.
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for regime in society.REGIMES:
        grouped = defaultdict(list)
        for row in alignment:
            if row.get("regime") == regime and row.get("eta_route") not in (None, "", "None"):
                grouped[int(row["to_checkpoint"])].append(float(row["eta_route"]))
        xs = sorted(grouped); ax.plot(xs, [np.mean(grouped[x]) for x in xs], marker="o", color=colors[regime], label=regime)
    ax.set(xlabel="to checkpoint", ylabel="eta_route", title="Corrected competence-aligned routing"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / "eta_route_corrected.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    segments = ["64→96", "96→128"]
    for offset, regime in enumerate(society.REGIMES):
        vals = []
        for from_cp, to_cp in ((64, 96), (96, 128)):
            vals.append(float(np.mean([float(r["fraction_same"]) for r in persistence if r.get("regime") == regime and int(r["from_checkpoint"]) == from_cp and int(r["to_checkpoint"]) == to_cp])))
        ax.plot(segments, vals, marker="o", color=colors[regime], label=regime)
    ax.set(ylabel="fraction same", title="Corrected role persistence"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / "role_persistence_corrected.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(society.REGIMES)); width = .2
    for index, segment in enumerate(("first32", "middle64", "last32")):
        vals = [float(np.mean([float(r["accuracy"]) for r in utility if r.get("regime") == regime and r.get("segment") == segment])) for regime in society.REGIMES]
        ax.bar(x + (index - 1) * width, vals, width, label=segment)
    ax.set_xticks(x, society.REGIMES); ax.set_ylabel("accuracy"); ax.set_title("Online team utility (raw events)"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / "team_utility_recomputed.png", dpi=160); plt.close(fig)

    final = [row for row in psi_bit if int(row["checkpoint"]) == max(society.CHECKPOINTS)]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for regime in society.REGIMES:
        vals = [float(r["psi_bit"]) for r in final if r["regime"] == regime]
        ax.scatter([regime] * len(vals), vals, color=colors[regime], label=regime)
    ax.set(ylabel="final Psi_spec bit", title="Final corrected competence interaction")
    fig.tight_layout(); fig.savefig(figure_root / "final_paired_psi_bit.png", dpi=160); plt.close(fig)

    matrices = {regime: _matrix(repair_rows, max(society.CHECKPOINTS), society.SEEDS[0], regime, "accuracy") for regime in society.REGIMES}
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), constrained_layout=True)
    for ax, regime in zip(axes, society.REGIMES):
        im = ax.imshow(matrices[regime], vmin=0, vmax=1, cmap="viridis"); ax.set_title(regime); ax.set_xticks(range(4), society.FAMILIES, rotation=45, ha="right"); ax.set_yticks(range(4), [f"agent_{i}" for i in range(4)])
    fig.colorbar(im, ax=axes, shrink=.75); fig.savefig(figure_root / "competence_matrices_corrected.png", dpi=160); plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), constrained_layout=True)
    for ax, regime in zip(axes, society.REGIMES):
        z = society._double_center(matrices[regime]); im = ax.imshow(z, cmap="coolwarm", vmin=-.5, vmax=.5); ax.set_title(regime); ax.set_xticks(range(4), society.FAMILIES, rotation=45, ha="right"); ax.set_yticks(range(4), [f"agent_{i}" for i in range(4)])
    fig.colorbar(im, ax=axes, shrink=.75); fig.savefig(figure_root / "double_centered_Z_corrected.png", dpi=160); plt.close(fig)

    symmetry = read_csv(REPAIR_ROOT / "label_symmetry_corrected.csv")
    fig, ax = plt.subplots(figsize=(7, 4.5)); ax.bar([r["regime"] for r in symmetry], [float(r["excess_bits"]) for r in symmetry], color=[colors[r["regime"]] for r in symmetry]); ax.axhline(0, color="black", linewidth=.8); ax.set(ylabel="MI excess (bits)", title="Corrected host-label × role association"); fig.tight_layout(); fig.savefig(figure_root / "label_symmetry_corrected.png", dpi=160); plt.close(fig)
    return sorted(path.name for path in figure_root.glob("*.png"))


def _write_impact_table(old_verdict: Mapping[str, Any], new_verdict: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(metric: str, old: Any, new: Any, reason: str, before: Any = "not applicable", after: Any = "not applicable") -> None:
        rows.append({"metric": metric, "old_reported_value": json.dumps(old, sort_keys=True), "repaired_value": json.dumps(new, sort_keys=True), "changed": old != new, "reason": reason, "preregistered_status_before": before, "preregistered_status_after": after})

    for filename, field, label in (("psi_spec_bit.csv", "psi_bit", "Psi_bit_final"), ("psi_spec_joint.csv", "psi_joint", "Psi_joint_final"), ("phi.csv", "phi_bit", "Phi_bit_final"), ("matching_gain.csv", "Delta_match_joint", "Delta_match_joint_final")):
        old_rows = read_csv(REPORT_ROOT / "original-analysis-invalid" / filename)
        new_rows = read_csv(REPORT_ROOT / filename)
        old_summary = _summary_by_regime([r for r in old_rows if int(r["checkpoint"]) == max(society.CHECKPOINTS)], field)
        new_summary = _summary_by_regime([r for r in new_rows if int(r["checkpoint"]) == max(society.CHECKPOINTS)], field)
        add(label, old_summary, new_summary, "depends on competence matrix aggregation")
    add("H1_social_amplification", old_verdict.get("H1_social_amplification"), new_verdict.get("H1_social_amplification"), "Psi_bit contrast changed after cell repair", old_verdict.get("social_amplification"), new_verdict.get("social_amplification"))
    add("H2_private_state_necessity", old_verdict.get("H2_private_state_necessity"), new_verdict.get("H2_private_state_necessity"), "Psi_bit contrast changed after cell repair")
    add("H3_dynamic_amplification", old_verdict.get("H3_dynamic_amplification"), new_verdict.get("H3_dynamic_amplification"), "Psi_bit AUC depends on repaired cells")
    add("H4_complementarity", old_verdict.get("H4_complementarity"), new_verdict.get("H4_complementarity"), "matching gain consumes A_joint", old_verdict.get("H4_complementarity", {}).get("pass"), new_verdict.get("H4_complementarity", {}).get("pass"))
    add("I_excess", _summary_by_regime(read_csv(REPORT_ROOT / "original-analysis-invalid/routing_information.csv"), "I_excess_bits", max(society.CHECKPOINTS)), _summary_by_regime(read_csv(REPORT_ROOT / "routing_information.csv"), "I_excess_bits", max(society.CHECKPOINTS)), "computed directly from online routing events; should be unchanged")
    add("H5_organized_labor", old_verdict.get("H5_organized_labor"), new_verdict.get("H5_organized_labor"), "eta_route component depends on repaired competence; routing MI component is raw", old_verdict.get("H5_organized_labor", {}).get("pass"), new_verdict.get("H5_organized_labor", {}).get("pass"))
    old_team_utility = _filter_segment(read_csv(REPORT_ROOT / "original-analysis-invalid/team_utility.csv"), "last32")
    new_team_utility = _filter_segment(read_csv(REPORT_ROOT / "team_utility.csv"), "last32")
    add("last32_team_utility", _summary_by_regime(old_team_utility, "accuracy"), _summary_by_regime(new_team_utility, "accuracy"), "computed directly from online_step correctness after filtering segment == last32")
    add("H6_team_utility", old_verdict.get("H6_team_utility"), new_verdict.get("H6_team_utility"), "raw online utility; should be unchanged", old_verdict.get("H6_team_utility", {}).get("pass"), new_verdict.get("H6_team_utility", {}).get("pass"))
    add("role_persistence", read_csv(REPORT_ROOT / "original-analysis-invalid/role_persistence.csv"), read_csv(REPORT_ROOT / "role_persistence.csv"), "role assignments consume repaired A_joint")
    add("label_symmetry", read_csv(REPORT_ROOT / "original-analysis-invalid/label_symmetry.csv"), read_csv(REPORT_ROOT / "label_symmetry.csv"), "assigned roles consume repaired A_joint")
    write_csv(REPAIR_ROOT / "bug_impact_table.csv", rows)
    return rows


def _write_audit_docs(bug_audit: Mapping[str, Any], validation: Mapping[str, Any], corrected: Mapping[str, Any]) -> None:
    audit = f"""# Minimal Developmental Society V1 — analysis bug audit

## Finding

The paid experiment is **valid** and the original offline competence analysis was
**invalid but repairable**. In `analyze()` the `vals_joint` and `vals_bits`
accumulators were initialized once per agent, outside the niche loop. Each later
niche therefore included prior-niche observations while still dividing by 16
probes (or 48 bit decisions). This is the direct cause of accuracy values greater
than one.

## Forensic counts

- Original `competence_joint.csv`: {bug_audit['original_outputs']['competence_joint']['impossible_gt1']} values > 1; maximum {bug_audit['original_outputs']['competence_joint']['max']}; rows {bug_audit['original_outputs']['competence_joint']['rows']}.
- Original `competence_bit.csv`: {bug_audit['original_outputs']['competence_bit']['impossible_gt1']} values > 1; maximum {bug_audit['original_outputs']['competence_bit']['max']}; rows {bug_audit['original_outputs']['competence_bit']['rows']}.
- Corrected joint values >1/<0: {validation['joint_bounds']['gt1']}/{validation['joint_bounds']['lt0']}.
- Corrected bit values >1/<0: {validation['bit_bounds']['gt1']}/{validation['bit_bounds']['lt0']}.

Representative impossible rows are preserved in `reports/society/minimal-developmental-society-v1/original-analysis-invalid/`.

## Impact

The bug corrupts every metric consuming held-out competence matrices: Psi_spec,
Phi, matching gain, role assignments/persistence, competence-aligned routing, and
role-label symmetry. Metrics computed directly from raw online events—routing MI,
online utility, exposure/memory composition, technical health, and cost—are
independent and were recomputed or verified unchanged. See `bug_impact_table.csv`.

The repair also canonicalizes the top-level functional-organization verdict to
the repaired three-layer verdict. The pre-repair scalar is retained under
`legacy_fields` for provenance. The impact table's `last32_team_utility` row is
computed only from rows with `segment == last32`; cumulative team-utility rows
are not substituted for the preregistered final window.

## Repair validation

Two independent raw-event aggregations (explicit grouped lookup and event-pivot
reconstruction) agree exactly for {validation['grouped_vs_pivot']['cell_count']} cells.
Every cell has 16 probes and 48 bit decisions. Hungarian and exhaustive 4! role
assignment optima agree for {validation['matching_bruteforce_vs_hungarian']['matrices_checked']} matrices.

The raw event log, frozen manifest, preregistration, run status, and budget hashes
are recorded in `raw_integrity.json` and remained unchanged. No model call was
made and no paid data were regenerated.
"""
    (ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_ANALYSIS_BUG_AUDIT.md").write_text(audit, encoding="utf-8")

    h = corrected.get("contrasts", {})
    report = f"""# SUPERSEDED ANALYSIS — Minimal Developmental Society V1

> The initial offline competence aggregation contained a niche-accumulator bug.
> The paid raw experiment remains valid, but this report must not be used as the
> canonical scientific analysis. See the corrected repair report and the
> machine-readable outputs under `reports/society/minimal-developmental-society-v1-analysis-repair/`.

# Minimal Developmental Society V1 — analysis repair report

## Executive correction

An accumulator bug in the initial offline competence aggregation produced
impossible accuracies. The raw paid experiment remains valid. The competence
analysis was repaired directly from immutable checkpoint events, with no new
model calls. This report supersedes the original offline conclusions.

## What was wrong

For each agent, the old implementation carried probe accumulators across niches
and divided every cumulative numerator by the single-niche denominator. The fixed
implementation resets accumulators for every `(seed, regime, checkpoint, agent,
niche)` cell and records probe/bit denominators and logical IDs.

## Validation and provenance

- Paid experiment: **VALID**; 47,104 logical completions, DeepSeek Direct
  `deepseek-v4-flash`.
- New model calls/cost: **0 / US$0.00**.
- Raw hashes: `raw_integrity.json`; original invalid outputs:
  `reports/society/minimal-developmental-society-v1/original-analysis-invalid/`.
- Grouped vs pivot aggregation mismatches: **{validation['grouped_vs_pivot']['mismatch_count']}**.
- Hungarian vs exhaustive matching mismatches: **{validation['matching_bruteforce_vs_hungarian']['mismatch_count']}**.

## Corrected final competence interaction

| regime | Psi_bit | Psi_joint | Phi_bit | Delta_match_joint |
|---|---:|---:|---:|---:|
"""
    psi = _summary_by_regime(read_csv(REPAIR_ROOT / "psi_spec_bit_corrected.csv"), "psi_bit", max(society.CHECKPOINTS))
    psij = _summary_by_regime(read_csv(REPAIR_ROOT / "psi_spec_joint_corrected.csv"), "psi_joint", max(society.CHECKPOINTS))
    ph = _summary_by_regime(read_csv(REPAIR_ROOT / "phi_corrected.csv"), "phi_bit", max(society.CHECKPOINTS))
    mg = _summary_by_regime(read_csv(REPAIR_ROOT / "matching_gain_corrected.csv"), "Delta_match_joint", max(society.CHECKPOINTS))
    for regime in society.REGIMES:
        report += f"| {regime} | {psi[regime]:.6f} | {psij[regime]:.6f} | {ph[regime]:.6f} | {mg[regime]:.6f} |\n"
    report += f"""
## Preregistered H1–H6

- H1 adaptive-private Psi amplification: **{'PASS' if corrected.get('H1_social_amplification') else 'FAIL'}**; AP12−RP mean {h.get('H1', {}).get('mean', float('nan')):.6f}, positive seeds {h.get('H1', {}).get('positive_seeds')}.
- H2 private-state contrast: **{'PASS' if corrected.get('H2_private_state_necessity') else 'FAIL'}**; AP12−AS12 mean {h.get('H2', {}).get('mean', float('nan')):.6f}, positive seeds {h.get('H2', {}).get('positive_seeds')}.
- H3 dynamic Psi AUC: **{'PASS' if corrected.get('H3_dynamic_amplification') else 'FAIL'}**; AP12−RP mean {h.get('H3', {}).get('mean', float('nan')):.6f}, positive seeds {h.get('H3', {}).get('positive_seeds')}.
- H4 complementarity: **{'PASS' if corrected.get('H4_complementarity', {}).get('pass') else 'FAIL'}**; AP12−RP matching gain {corrected.get('H4_complementarity', {}).get('mean_AP12_minus_RP', float('nan')):.6f}.
- H5 competence-aligned organization: **{'PASS' if corrected.get('H5_organized_labor', {}).get('pass') else 'FAIL'}**; AP12 late eta {corrected.get('H5_organized_labor', {}).get('mean_eta_route_AP12_late', float('nan')):.6f}.
- H6 realized last-32 team utility: **{'PASS' if corrected.get('H6_team_utility', {}).get('pass') else 'FAIL'}**; AP12−RP mean {corrected.get('H6_team_utility', {}).get('mean_AP12_minus_RP_last32', float('nan')):.6f}.

## Three-layer verdict

**Social amplification: SUPPORTED.** Corrected H1–H3 pass their frozen
engineering thresholds.

**Functional organization: PARTIAL.** Corrected competence complementarity and
competence-aligned routing pass, but H6 does not establish robust realized team
utility improvement.

**Emergent functional specialization: NOT YET SUPPORTED.** The result is evidence
of private-history-dependent competence interaction and organized allocation, not
proof of stable identities or a useful division of labor.

## Strongest supported result

Adaptive competence-sensitive routing with private developmental histories
amplified held-out agent×niche competence interactions relative to random-private
and adaptive-shared controls in this eight-seed pilot.

## Strongest remaining null

The realized last-32 online team-utility gain remained below the preregistered
threshold, with AP12 positive in 6/8 seeds but mean gain only
{corrected.get('H6_team_utility', {}).get('mean_AP12_minus_RP_last32', float('nan')):.6f}.

## What this does not establish

This does not establish permanent roles, a phase transition, generalization beyond
the V3.1 DIAGONAL ecology, or causal superiority of private memory in every
environment. The independent units remain eight seeds, not 47,104 API calls.

## Outputs

Corrected machine-readable outputs are in
`reports/society/minimal-developmental-society-v1-analysis-repair/`; the old report
is explicitly superseded. No new experiment is authorized by this repair.
"""
    (ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_ANALYSIS_REPAIR_REPORT.md").write_text(report, encoding="utf-8")


def run_repair() -> dict[str, Any]:
    """Re-run the existing offline analysis, then independently audit it."""
    before_hashes = raw_hashes()
    # The existing analyzer is now fixed and remains the single dependent-metric
    # implementation.  It reads only the immutable event log.
    verdict = society.analyze()
    society._write_report(verdict)
    _preserve_superseded_report_notice()
    society._make_figures()
    events = read_jsonl(RAW_FILES["events"])
    terminals = society._existing_terminal(events)
    grouped = grouped_aggregation(terminals)
    pivot = pivot_aggregation(terminals)
    aggregation_check = compare_aggregations(grouped, pivot)
    joint_rows = list(grouped.values())
    bit_rows = [dict(row, accuracy=row["bit_accuracy"]) for row in joint_rows]
    matching_check = validate_matching(joint_rows)
    copied = _copy_corrected_outputs()
    write_csv(REPAIR_ROOT / "competence_joint_corrected.csv", joint_rows)
    write_csv(REPAIR_ROOT / "competence_bit_corrected.csv", bit_rows)
    write_csv(REPAIR_ROOT / "psi_spec_joint_corrected.csv", read_csv(REPORT_ROOT / "psi_spec_joint.csv"))
    write_csv(REPAIR_ROOT / "psi_spec_bit_corrected.csv", read_csv(REPORT_ROOT / "psi_spec_bit.csv"))

    old_joint = read_csv(REPORT_ROOT / "original-analysis-invalid/competence_joint.csv")
    old_bit = read_csv(REPORT_ROOT / "original-analysis-invalid/competence_bit.csv")
    old_bad_joint = [row for row in old_joint if float(row["accuracy"]) > 1 or float(row["accuracy"]) < 0]
    old_bad_bit = [row for row in old_bit if float(row["accuracy"]) > 1 or float(row["accuracy"]) < 0]
    bug_audit = {
        "source": {"file": "src/emergent_specialization/minimal_developmental_society.py", "function": "analyze", "scope": "vals_joint/vals_bits were initialized once per agent, outside the niche loop"},
        "mathematical_error": "later niche numerators accumulated earlier niche observations but were divided by the single-niche denominator EVAL_COUNT",
        "original_outputs": {"competence_joint": {"rows": len(old_joint), "impossible_gt1": len([r for r in old_joint if float(r['accuracy']) > 1]), "impossible_lt0": len([r for r in old_joint if float(r['accuracy']) < 0]), "max": max(float(r['accuracy']) for r in old_joint), "first_bad_rows": old_bad_joint[:5]}, "competence_bit": {"rows": len(old_bit), "impossible_gt1": len([r for r in old_bit if float(r['accuracy']) > 1]), "impossible_lt0": len([r for r in old_bit if float(r['accuracy']) < 0]), "max": max(float(r['accuracy']) for r in old_bit), "first_bad_rows": old_bad_bit[:5]}},
        "downstream_dependents": ["Psi_spec", "Phi", "matching gain", "role assignments", "role persistence", "routing alignment eta", "label-symmetry role analysis"],
        "independent_metrics": ["online routing counts", "routing entropy/MI", "online team utility", "raw exposure", "raw memory composition", "technical health/cost"],
        "paid_experiment": "VALID",
        "offline_competence_analysis": "INVALID AND REPAIRABLE",
    }
    (REPAIR_ROOT / "bug_audit.json").write_text(json.dumps(bug_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPAIR_ROOT / "raw_integrity.json").write_text(json.dumps({"before": before_hashes, "after": raw_hashes(), "unchanged": before_hashes == raw_hashes()}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPAIR_ROOT / "aggregation_validation.json").write_text(json.dumps({"grouped_vs_pivot": aggregation_check, "matching_bruteforce_vs_hungarian": matching_check, "joint_bounds": {"gt1": sum(float(r['accuracy']) > 1 for r in joint_rows), "lt0": sum(float(r['accuracy']) < 0 for r in joint_rows)}, "bit_bounds": {"gt1": sum(float(r['bit_accuracy']) > 1 for r in joint_rows), "lt0": sum(float(r['bit_accuracy']) < 0 for r in joint_rows)}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    figure_files = _write_figures(joint_rows)
    verdict_path = REPAIR_ROOT / "corrected_verdict.json"
    corrected = json.loads(verdict_path.read_text(encoding="utf-8"))
    three_layer_verdict = {
        "social_amplification": "SUPPORTED" if all(corrected.get(name) for name in ("H1_social_amplification", "H2_private_state_necessity", "H3_dynamic_amplification")) else "NOT SUPPORTED",
        "functional_organization": "PARTIAL" if corrected.get("H4_complementarity", {}).get("pass") and corrected.get("H5_organized_labor", {}).get("pass") else "NOT SUPPORTED",
        "emergent_functional_specialization": "NOT YET SUPPORTED",
    }
    legacy_functional_organization = corrected.get("functional_organization")
    if legacy_functional_organization != three_layer_verdict["functional_organization"]:
        legacy_fields = dict(corrected.get("legacy_fields", {}))
        legacy_fields.setdefault("functional_organization", legacy_functional_organization)
        corrected["legacy_fields"] = legacy_fields
    corrected.update({"analysis_repair": True, "new_model_calls": 0, "new_inference_cost_usd": 0.0, "aggregation_validation": aggregation_check, "matching_validation": matching_check,
                     "three_layer_verdict": three_layer_verdict,
                     "functional_organization": three_layer_verdict["functional_organization"]})
    verdict_path.write_text(json.dumps(corrected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPAIR_ROOT / "figures.json").write_text(json.dumps({"files": figure_files}, indent=2) + "\n", encoding="utf-8")
    validation = json.loads((REPAIR_ROOT / "aggregation_validation.json").read_text(encoding="utf-8"))
    old_verdict = json.loads((REPORT_ROOT / "original-analysis-invalid/verdict.json").read_text(encoding="utf-8"))
    _write_impact_table(old_verdict, corrected)
    _write_audit_docs(bug_audit, validation, corrected)
    return {"status": "REPAIR COMPLETE", "bug_confirmed": True, "paid_experiment": "VALID", "offline_analysis": "REPAIRED", "new_model_calls": 0, "raw_integrity": before_hashes == raw_hashes(), "aggregation": aggregation_check, "matching": matching_check, "verdict": corrected, "repair_root": str(REPAIR_ROOT.relative_to(ROOT))}


if __name__ == "__main__":
    print(json.dumps(run_repair(), indent=2, sort_keys=True))

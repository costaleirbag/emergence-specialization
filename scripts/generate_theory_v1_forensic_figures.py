"""Generate deterministic Theory V1 forensic figures from repair artifacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/theory-v1/repair"
FIG = OUT / "figures"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    score = json.loads((OUT / "theory_v1_scorecard_repaired.json").read_text())
    predictions = score["prediction_rows"]
    observed = {tuple([r["ecology"], int(r["k"]), float(r["beta"]), float(r["epsilon"]), float(r["q_share"])]): r for r in score["observed_cell_rows"]}
    keys = lambda r: (r["ecology"], int(r["k"]), float(r["beta"]), float(r["epsilon"]), float(r["q_share"]))
    # Repaired predicted-vs-observed growth, pooled and per ecology.
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharex=True, sharey=True)
    for ax, ecology in zip(axes, ["ALL", "V31_FRESH", "AFFINE_BOOLEAN_V1"]):
        rows = [r for r in predictions if ecology == "ALL" or r["ecology"] == ecology]
        ax.scatter([r["g_excess_pred"] for r in rows], [observed[keys(r)]["g_excess_obs"] for r in rows], s=20, alpha=.75)
        ax.axline((0, 0), slope=1, color="0.5", linestyle="--", linewidth=.8)
        ax.set_title(ecology); ax.set_xlabel("predicted excess growth")
    axes[0].set_ylabel("observed excess growth"); save(fig, "predicted_vs_observed_growth.png")

    # Beta response panels.
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True, sharey=True)
    for ax, (ecology, k) in zip(axes.flat, [(e, k) for e in ("V31_FRESH", "AFFINE_BOOLEAN_V1") for k in (4, 8, 12)]):
        rows = sorted([r for r in predictions if r["ecology"] == ecology and int(r["k"]) == k and float(r["q_share"]) == 0], key=lambda r: r["beta"])
        ax.plot([r["beta"] for r in rows], [r["g_excess_pred"] for r in rows], "o-", label="predicted")
        ax.plot([r["beta"] for r in rows], [observed[keys(r)]["g_excess_obs"] for r in rows], "s--", label="observed")
        ax.set_title(f"{ecology} k={k}"); ax.set_xlabel("beta")
    axes[0, 0].set_ylabel("excess growth"); axes[1, 0].set_ylabel("excess growth"); axes[0, 0].legend(fontsize=8); save(fig, "beta_response.png")

    # Capacity and sharing laws.
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ecology in ("V31_FRESH", "AFFINE_BOOLEAN_V1"):
        rows = sorted([r for r in predictions if r["ecology"] == ecology and float(r["beta"]) == 12 and float(r["q_share"]) == 0], key=lambda r: r["k"])
        axes[0].plot([r["k"] for r in rows], [r["g_excess_pred"] for r in rows], "o-", label=f"pred {ecology}")
        axes[0].plot([r["k"] for r in rows], [observed[keys(r)]["g_excess_obs"] for r in rows], "s--", label=f"obs {ecology}")
        rows = [r for r in predictions if r["ecology"] == ecology and int(r["k"]) == 8 and float(r["beta"]) == 12]
        for r in rows: axes[1].scatter(r["q_share"], observed[keys(r)]["g_excess_obs"], label=ecology if r["q_share"] == 0 else None)
    axes[0].set(title="capacity law", xlabel="k", ylabel="excess growth"); axes[1].set(title="sharing response", xlabel="q", ylabel="observed excess growth"); axes[0].legend(fontsize=7); save(fig, "capacity_and_sharing.png")

    # Matched effective gain, per ecology using seed-level observed rows.
    seed_rows = read_csv(OUT / "observed_seed_cell_metrics.csv")
    fig, ax = plt.subplots(figsize=(7, 4))
    for ecology in ("V31_FRESH", "AFFINE_BOOLEAN_V1"):
        left = {(int(r["seed"]), int(r["cell_id"])): float(r["g_obs_bit"]) for r in seed_rows if r["ecology"] == ecology and int(r["k"]) == 8 and float(r["beta"]) == 8 and float(r["epsilon"]) == .1 and float(r["q_share"]) == 0}
        right = {(int(r["seed"]), int(r["cell_id"])): float(r["g_obs_bit"]) for r in seed_rows if r["ecology"] == ecology and int(r["k"]) == 8 and float(r["beta"]) == 16 and float(r["epsilon"]) == .55 and float(r["q_share"]) == 0}
        diffs = [left[k] - right[k] for k in sorted(set(left) & set(right))]
        ax.plot(range(len(diffs)), diffs, "o-", label=ecology)
    ax.axhline(.002, color="0.5", linestyle="--"); ax.axhline(-.002, color="0.5", linestyle="--"); ax.set(title="matched effective gain: seed/cell differences", xlabel="paired unit", ylabel="g(8,.1) − g(16,.55)"); ax.legend(); save(fig, "matched_gain.png")

    # Repaired R_spec and regime map.
    fig, ax = plt.subplots(figsize=(10, 4)); rows = sorted(predictions, key=lambda r: (r["ecology"], int(r["k"]), float(r["beta"]), float(r["q_share"])))
    colors = {"SUBCRITICAL": "#4c78a8", "TRANSITIONAL": "#f2cf5b", "SUPERCRITICAL": "#e45756"}
    ax.bar(np.arange(len(rows)), [r["R_spec"] for r in rows], color=[colors[r["regime"]] for r in rows]); ax.axhline(.98, color="0.4", linestyle="--"); ax.axhline(1.02, color="0.4", linestyle="--"); ax.set(title="repaired centered R_spec", xlabel="population cell", ylabel="R_spec"); save(fig, "repaired_rspec_regimes.png")

    # K heatmaps.
    kdata = json.loads((OUT / "k_reconstruction.json").read_text())["pooled"]
    fig, axes = plt.subplots(2, 3, figsize=(10, 6), sharex=True, sharey=True)
    for ax, (e, k) in zip(axes.flat, [(e, k) for e in ("V31_FRESH", "AFFINE_BOOLEAN_V1") for k in (4, 8, 12)]):
        ax.imshow(np.asarray(kdata[e][str(k)]), cmap="coolwarm", vmin=-.1, vmax=.1); ax.set_title(f"{e} K({k})"); ax.set_xticks(range(4)); ax.set_yticks(range(4))
    save(fig, "K_heatmaps.png")

    # Micro superposition summary.
    lin = read_csv(OUT / "micro_linearity_diagnostics.csv"); fig, ax = plt.subplots(figsize=(8, 4))
    for e in ("V31_FRESH", "AFFINE_BOOLEAN_V1"):
        for k in (4, 8, 12):
            vals = [float(r["r2"]) for r in lin if r["ecology"] == e and int(r["k"]) == k]
            ax.scatter([f"{e[:3]}-{k}"] * len(vals), vals, label=f"{e} k={k}")
    ax.axhline(0, color="0.5", linestyle="--"); ax.set(title="MICRO double-swap R²", ylabel="R²"); save(fig, "micro_superposition_r2.png")

    # Psi trajectories and secondary formation/exploitation summary.
    sec = read_csv(OUT / "formation_exploitation_secondary.csv"); fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for e in ("V31_FRESH", "AFFINE_BOOLEAN_V1"):
        subset = [r for r in sec if r["ecology"] == e]
        for metric, ax in zip(("psi_bit", "delta_match", "team_accuracy"), axes):
            vals = {}
            for r in subset: vals.setdefault(int(r["checkpoint"]), []).append(float(r[metric]))
            points = sorted((t, np.mean(v)) for t, v in vals.items())
            ax.plot([p[0] for p in points], [p[1] for p in points], "o-", label=e)
            ax.set_xlabel("checkpoint"); ax.set_title(metric)
    axes[0].set_ylabel("value"); axes[0].legend(fontsize=7); save(fig, "formation_vs_exploitation.png")

    # Scorecard statuses.
    names = list(score["tests"]); statuses = [score["tests"][n]["status"] for n in names]; colors2 = [{"PASS": "#59a14f", "FAIL": "#e15759", "NON_IDENTIFIABLE": "#bab0ab"}[s] for s in statuses]
    fig, ax = plt.subplots(figsize=(9, 3)); ax.bar(names, [1] * len(names), color=colors2); ax.set_yticks([]); ax.set_title("Theory V1 repaired T1–T9 scorecard");
    for i, status in enumerate(statuses): ax.text(i, .5, status, ha="center", va="center", fontsize=8, rotation=90)
    save(fig, "scorecard_T1_T9.png")


if __name__ == "__main__":
    main()

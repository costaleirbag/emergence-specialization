"""Generate offline Local Plasticity Curve V1 figures."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/task-ecology/local-plasticity-curve-v1/figures"
DATA = ROOT / "reports/task-ecology/local-plasticity-curve-v1"
H = [1, 2, 4, 8]


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=170)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    curves = rows("plasticity_curves.csv")
    gains = rows("absolute_gain.csv")
    rels = rows("relative_gain.csv")
    foreign = rows("foreign_context_effect.csv")
    dose = rows("dose_response.csv")
    niche = rows("niche_level_accuracy.csv")
    component = rows("component_curves.csv")
    bayes = rows("bayes_curve.csv")
    foreign_source = rows("foreign_source_accuracy.csv")
    anchor = rows("anchoring.csv")
    history = rows("historical_v2_replication.csv")

    # 1. Main empirical curve.
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for condition, color, marker in (("SAME", "#244f78", "o"), ("FOREIGN", "#b55a45", "s")):
        rr = [r for r in curves if r["condition"] == condition]
        ax.errorbar([int(r["h"]) for r in rr], [float(r["accuracy"]) for r in rr], yerr=[float(r["sample_sd"]) for r in rr], marker=marker, color=color, label=condition, capsize=3)
    empty = next(r for r in curves if r["condition"] == "EMPTY")
    ax.axhline(float(empty["accuracy"]), color="#555", linestyle="--", label="EMPTY A0")
    ax.set(xlabel="natural history horizon h", ylabel="joint exact accuracy", title="Local plasticity curve — DIAGONAL ecology")
    ax.set_xticks(H); ax.set_ylim(0, .55); ax.legend()
    save(fig, "01_empirical_curves.png")

    # 2–4. Gain curves.
    for filename, data, field, title, color in (("02_absolute_gain.png", gains, "G_abs", "Absolute local plasticity", "#244f78"), ("03_relative_gain.png", rels, "G_rel", "Relative local advantage", "#6a3d75"), ("04_foreign_context_effect.png", foreign, "G_foreign", "Foreign-context effect", "#b55a45")):
        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        for seed in sorted({int(r["seed"]) for r in data}):
            rr = [r for r in data if int(r["seed"]) == seed]
            ax.plot([int(r["h"]) for r in rr], [float(r[field]) for r in rr], marker="o", alpha=.8, label=str(seed))
        agg = {int(r["h"]): float(r[field]) for r in data}
        ax.plot(H, [agg[h] for h in H], color=color, linewidth=3, label="mean")
        ax.axhline(0, color="#555", linewidth=.8); ax.set_xticks(H); ax.set(xlabel="h", ylabel=field, title=title); ax.legend(fontsize=7, ncol=3)
        save(fig, filename)

    # 5. Per-seed same/foreign curves.
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharex=True, sharey=True)
    for ax, seed in zip(axes.ravel(), sorted({int(r["seed"]) for r in gains})):
        same = {int(r["h"]): float(r["G_abs"]) for r in gains if int(r["seed"]) == seed}
        rel = {int(r["h"]): float(r["G_rel"]) for r in rels if int(r["seed"]) == seed}
        ax.plot(H, [same[h] for h in H], "o-", label="G_abs", color="#244f78"); ax.plot(H, [rel[h] for h in H], "s-", label="G_rel", color="#6a3d75"); ax.axhline(0, color="#555", linewidth=.7); ax.set_title(f"seed {seed}"); ax.set_xticks(H)
    axes[0, 0].legend(fontsize=7); fig.supxlabel("h"); fig.supylabel("gain"); fig.suptitle("Seed-level plasticity")
    save(fig, "05_per_seed_gains.png")

    # 6. Per-niche curves.
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharex=True, sharey=True)
    for ax, target in zip(axes.ravel(), sorted({r["target"] for r in niche})):
        same = [r for r in niche if r["target"] == target and r["condition"] == "SAME"]
        foreign = [r for r in niche if r["target"] == target and r["condition"] == "FOREIGN"]
        mean_same = [np.mean([float(r["accuracy"]) for r in same if int(r["h"]) == h]) for h in H]
        mean_foreign = [np.mean([float(r["accuracy"]) for r in foreign if int(r["h"]) == h]) for h in H]
        base = np.mean([float(r["accuracy"]) for r in niche if r["target"] == target and r["condition"] == "EMPTY"])
        ax.plot(H, mean_same, "o-", color="#244f78", label="SAME"); ax.plot(H, mean_foreign, "s-", color="#b55a45", label="FOREIGN"); ax.axhline(base, linestyle="--", color="#555", label="A0"); ax.set_title(target); ax.set_xticks(H)
    axes[0, 0].legend(fontsize=7); fig.supxlabel("h"); fig.supylabel("accuracy"); fig.suptitle("Niche-level curves")
    save(fig, "06_per_niche_curves.png")

    # 7. Components.
    fig, ax = plt.subplots(figsize=(7, 4))
    for condition, color in (("SAME", "#244f78"), ("FOREIGN", "#b55a45")):
        for bit in ("1", "2", "3"):
            rr = [r for r in component if r["condition"] == condition and r["component"] == bit]
            ax.plot([int(r["h"]) for r in rr], [float(r["accuracy"]) for r in rr], marker="o", color=color, alpha=.45, label=f"{condition} bit {bit}")
    ax.set_xticks([0] + H); ax.set(xlabel="h", ylabel="component accuracy", title="Component-level response curves"); ax.legend(fontsize=6, ncol=2)
    save(fig, "07_component_curves.png")

    # 8. Bayes vs DeepSeek.
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    empirical = {("EMPTY", 0): float(next(r["accuracy"] for r in curves if r["condition"] == "EMPTY"))}
    empirical.update({(r["condition"], int(r["h"])): float(r["accuracy"]) for r in curves if r["condition"] != "EMPTY"})
    for condition, color in (("SAME", "#244f78"), ("FOREIGN", "#b55a45")):
        rr = [r for r in bayes if r["condition"] == condition]
        ax.plot(H, [float(r["A_star"]) for r in rr], "--", color=color, label=f"Bayes {condition}")
        ax.plot(H, [empirical[(condition, h)] for h in H], "o-", color=color, label=f"DeepSeek {condition}")
    ax.axhline(.125, color="#555", linestyle=":", label="Bayes EMPTY"); ax.set_xticks(H); ax.set(xlabel="h", ylabel="accuracy", title="Ecological opportunity vs realized learning"); ax.legend(fontsize=7)
    save(fig, "08_bayes_vs_deepseek.png")

    # 9. h8 seed scatter.
    fig, ax = plt.subplots(figsize=(5.2, 4.5))
    for i, seed in enumerate(sorted({int(r["seed"]) for r in gains})):
        x = float(next(r["G_abs"] for r in gains if int(r["seed"]) == seed and int(r["h"]) == 8)); y = float(next(r["G_rel"] for r in rels if int(r["seed"]) == seed and int(r["h"]) == 8)); ax.scatter(x, y, s=55, label=str(seed)); ax.text(x + .005, y + .005, str(seed), fontsize=8)
    ax.axhline(0, color="#555", linewidth=.7); ax.axvline(0, color="#555", linewidth=.7); ax.set(xlabel="G_abs(8)", ylabel="G_rel(8)", title="h8 local advantage by seed"); ax.legend(fontsize=7)
    save(fig, "09_h8_gain_scatter.png")

    # 10. Foreign-source effects at h8.
    fig, ax = plt.subplots(figsize=(7, 4)); targets = sorted({r["target"] for r in foreign_source}); sources = sorted({r["source"] for r in foreign_source}); mat = np.full((4, 4), np.nan)
    for r in foreign_source:
        if int(r["h"]) == 8: mat[targets.index(r["target"]), sources.index(r["source"])] = float(r["accuracy"])
    im = ax.imshow(mat, vmin=0, vmax=.5, cmap="magma"); ax.set_xticks(range(4), sources, rotation=35, ha="right"); ax.set_yticks(range(4), targets); ax.set(xlabel="foreign source", ylabel="target niche", title="Foreign-source accuracy at h=8"); fig.colorbar(im, ax=ax, fraction=.046)
    for i in range(4):
        for j in range(4):
            if np.isfinite(mat[i, j]): ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center", color="white")
    save(fig, "10_foreign_source_heatmap.png")

    # 11. Anchoring correctness.
    fig, ax = plt.subplots(figsize=(7, 4))
    for condition, color in (("SAME", "#244f78"), ("FOREIGN", "#b55a45")):
        rr = [r for r in anchor if r["condition"] == condition]
        xs = []; ys = []
        for h in H:
            copied = [int(r["correct"]) for r in rr if int(r["h"]) == h and int(r["any_action_copy"]) == 1]; notcopied = [int(r["correct"]) for r in rr if int(r["h"]) == h and int(r["any_action_copy"]) == 0]
            xs.append(h); ys.append((np.mean(copied) if copied else np.nan, np.mean(notcopied) if notcopied else np.nan))
        ax.plot(xs, [v[0] for v in ys], "o-", color=color, label=f"{condition} copied"); ax.plot(xs, [v[1] for v in ys], "--", color=color, label=f"{condition} not copied")
    ax.set_xticks(H); ax.set(xlabel="h", ylabel="correctness", title="Anchoring diagnostic"); ax.legend(fontsize=7, ncol=2)
    save(fig, "11_anchoring_correctness.png")

    # 12. Historical V2 replication.
    fig, ax = plt.subplots(figsize=(7, 4)); x = np.arange(4); width = .18
    for offset, field, label, color in ((-.27, "v2_G_abs_h8", "V2 G_abs", "#999"), (-.09, "v2_G_rel_h8", "V2 G_rel", "#d4a72c"), (.09, "current_G_abs", "Current G_abs", "#244f78"), (.27, "current_G_rel", "Current G_rel", "#6a3d75")):
        values = []
        for r in history:
            seed = int(r["seed"]); values.append(float(r[field]) if field in r else float(next(g["G_abs"] for g in gains if int(g["seed"]) == seed and int(g["h"]) == 8) if label == "Current G_abs" else next(g["G_rel"] for g in rels if int(g["seed"]) == seed and int(g["h"]) == 8)))
        ax.bar(x + offset, values, width, label=label, color=color)
    ax.set_xticks(x, [r["seed"] for r in history]); ax.axhline(0, color="#555", linewidth=.7); ax.set(ylabel="gain", title="Historical V2 vs contemporaneous curve"); ax.legend(fontsize=7)
    save(fig, "12_historical_v2_replication.png")
    (OUT / "README.txt").write_text("Generated offline by scripts/generate_local_plasticity_figures.py; no model calls.\n", encoding="utf-8")


if __name__ == "__main__":
    main()

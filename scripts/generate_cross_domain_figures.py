"""Generate offline figures for Cross-Domain Transfer Bottleneck V1.

This script consumes only frozen reports and raw-derived CSVs; it never calls a
model.  It intentionally keeps the plots small and audit-friendly.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/task-ecology/cross-domain-transfer-bottleneck-v1/figures"
V31 = ROOT / "reports/task-ecology/ecological-information-v31"
DATA = ROOT / "reports/task-ecology/cross-domain-transfer-bottleneck-v1"
FAMILIES = ["ACCESS", "RELEASE", "INCIDENT", "PROVENANCE"]
GEOMETRIES = ["GLOBAL", "BLOCK", "DIAGONAL"]


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_heatmap(values, title, filename, *, vmin=0.0, vmax=1.0, cmap="viridis"):
    fig, ax = plt.subplots(figsize=(5.1, 4.3), constrained_layout=True)
    im = ax.imshow(values, vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_xticks(range(4), FAMILIES, rotation=35, ha="right")
    ax.set_yticks(range(4), FAMILIES)
    ax.set_xlabel("target niche")
    ax.set_ylabel("source niche")
    ax.set_title(title, fontsize=10)
    for i in range(4):
        for j in range(4):
            if np.isfinite(values[i, j]):
                ax.text(j, i, f"{values[i,j]:.2f}", ha="center", va="center", fontsize=8,
                        color="white" if values[i, j] < (vmax + vmin) / 2 else "black")
    fig.colorbar(im, ax=ax, fraction=.046, pad=.04)
    fig.savefig(OUT / filename, dpi=170)
    plt.close(fig)


def matrix(rows, *, geometry, arm, value="accuracy"):
    out = np.full((4, 4), np.nan)
    for r in rows:
        if r["geometry"] == geometry and r["arm"] == arm:
            try:
                out[FAMILIES.index(r["source"]), FAMILIES.index(r["target"])] = float(r[value])
            except (ValueError, TypeError):
                pass
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jrows = [r for r in read_csv(V31 / "observable_J_natural.csv") if r["h"] == "8"]
    lrows = [r for r in read_csv(V31 / "observable_Lstar_natural.csv") if r["h"] == "8"]
    for g in GEOMETRIES:
        j = np.full((4, 4), np.nan); l = np.full((4, 4), np.nan)
        for r in jrows:
            if r["geometry"] == g: j[FAMILIES.index(r["source"]), FAMILIES.index(r["target"])] = float(r["L_star"])
        for r in lrows:
            if r["geometry"] == g: l[FAMILIES.index(r["source"]), FAMILIES.index(r["target"])] = float(r["L_star"])
        save_heatmap(j, f"Observable J / Bayes gain — {g} (h=8)", f"theory_J_{g.lower()}.png", vmax=max(1.0, float(np.nanmax(j))))
        save_heatmap(l, f"Observable L* — {g} (h=8)", f"theory_Lstar_{g.lower()}.png", vmax=max(1.0, float(np.nanmax(l))))

    rows = read_csv(DATA / "aggregate_transfer_matrices.csv")
    for g in GEOMETRIES:
        for arm in ("LOCAL_REP", "A0_RELATION_ONLY", "A1_SEMANTIC_PI", "A2_CANONICAL", "A3_RULE_SEMANTIC", "A4_RULE_CANONICAL"):
            save_heatmap(matrix(rows, geometry=g, arm=arm), f"DeepSeek {arm} — {g}", f"empirical_{arm.lower()}_{g.lower()}.png")

    # Compact gate-facing summaries.
    ladder = read_csv(DATA / "ladder_summary.csv")
    arms = [r["condition"] for r in ladder]
    vals = [float(r["joint_accuracy"]) for r in ladder]
    fig, ax = plt.subplots(figsize=(7.2, 3.5), constrained_layout=True)
    ax.bar(arms, vals, color=["#5064a8", "#b75d43", "#d1833f", "#6b9e78", "#718091", "#34495e"])
    ax.set_ylim(0, 1.05); ax.set_ylabel("joint exact accuracy"); ax.set_title("Frozen ladder — semantic-to-canonical diagnostic")
    ax.tick_params(axis="x", rotation=28)
    for i, v in enumerate(vals): ax.text(i, v + .02, f"{v:.3f}", ha="center", fontsize=8)
    fig.savefig(OUT / "ladder_accuracy.png", dpi=170); plt.close(fig)

    geom = read_csv(DATA / "geometry_metrics.csv")
    fig, ax = plt.subplots(figsize=(7.0, 3.8), constrained_layout=True)
    for arm, color in [("A0_RELATION_ONLY", "#b75d43"), ("A1_SEMANTIC_PI", "#d1833f"), ("A2_CANONICAL", "#5064a8"), ("A3_RULE_SEMANTIC", "#718091"), ("A4_RULE_CANONICAL", "#34495e")]:
        means = []
        for g in GEOMETRIES:
            xs = [float(r["O_cross"]) for r in geom if r["arm"] == arm and r["geometry"] == g and r["O_cross"] not in ("", "nan", "NaN")]
            means.append(np.mean(xs) if xs else np.nan)
        ax.plot(GEOMETRIES, means, marker="o", label=arm, color=color)
    ax.set_ylim(0, 1.05); ax.set_ylabel("cross-domain accuracy"); ax.set_title("Cross-domain realized transfer by frozen arm"); ax.legend(fontsize=7)
    fig.savefig(OUT / "cross_domain_ladder_by_geometry.png", dpi=170); plt.close(fig)

    # Component accuracies and anchoring are diagnostic, not primary outcomes.
    comp = read_csv(DATA / "component_metrics.csv")
    fig, ax = plt.subplots(figsize=(7.2, 3.6), constrained_layout=True)
    for arm in ("LOCAL_REP", "A0_RELATION_ONLY", "A1_SEMANTIC_PI", "A2_CANONICAL", "A3_RULE_SEMANTIC", "A4_RULE_CANONICAL"):
        vals = [float(next(r["accuracy"] for r in comp if r["condition"] == arm and r["component"] == str(i))) for i in range(1, 4)]
        ax.plot([1, 2, 3], vals, marker="o", label=arm)
    ax.set_xticks([1, 2, 3]); ax.set_ylim(0, 1.05); ax.set_xlabel("decision component"); ax.set_ylabel("accuracy"); ax.set_title("Component-level accuracy (descriptive)"); ax.legend(fontsize=6, ncol=2)
    fig.savefig(OUT / "component_accuracy.png", dpi=170); plt.close(fig)

    # A manifest for downstream decks/reports.
    (OUT / "README.txt").write_text("Generated offline by scripts/generate_cross_domain_figures.py; no model calls.\n", encoding="utf-8")


if __name__ == "__main__":
    main()

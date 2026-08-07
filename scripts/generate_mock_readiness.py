#!/usr/bin/env python3
"""Generate clearly labelled synthetic readiness figures without any model calls.

The script exercises the real ExperimentRunner with MockBackend for a tiny
PRIVATE/SHARED pair, then derives presentation-style plots from those artifacts.
Everything is written below ``reports/mock-readiness`` (ignored by Git).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from emergent_specialization.analysis import checkpoint_rows, load_run
from emergent_specialization.config import AgentSettings, ConditionSettings, ExperimentSettings, LoggingSettings, RunConfig
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.experiment import ExperimentRunner
from emergent_specialization.metrics.online import online_observables
from emergent_specialization.probes import generate_probe_payload, write_probe_set
from emergent_specialization.providers.mock import MockBackend


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "mock-readiness"


def _watermark(fig: Any) -> None:
    fig.text(
        0.5,
        0.02,
        "MOCK / SYNTHETIC — NOT SCIENTIFIC DATA",
        ha="center",
        va="bottom",
        fontsize=10,
        color="#b42318",
        alpha=0.9,
        weight="bold",
    )


def _save(fig: Any, name: str) -> None:
    _watermark(fig)
    fig.savefig(OUTPUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _run_mock_pair() -> tuple[Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    probe_path = OUTPUT / "mock_probe_set.json"
    write_probe_set(probe_path, generate_probe_payload(HiddenWorldEnvironment(), seed=17, per_world=2))
    runs: dict[str, Path] = {}
    for condition in ("private", "shared"):
        config = RunConfig(
            experiment=ExperimentSettings(
                num_agents=2,
                num_rounds=3,
                checkpoints=(0, 2, 3),
                seed=1,
                task_seed=101,
                router_seed=102,
                feedback_seed=103,
                max_concurrency=2,
                technical_retries=0,
                console_summary=False,
            ),
            agent=AgentSettings(backend="mock", memory_k=3),
            condition=ConditionSettings(memory_mode=condition),
            logging=LoggingSettings(
                output_dir=str(OUTPUT / "mock_runs" / condition),
                probe_set_path=str(probe_path),
            ),
        )
        runs[condition] = asyncio.run(ExperimentRunner(config, backend=MockBackend()).run())
    return runs["private"], runs["shared"]


def _matrix(checkpoint: dict[str, Any], key: str) -> tuple[list[str], list[str], np.ndarray]:
    agents = [str(value) for value in checkpoint.get("agent_ids", [])]
    if key == "competence_matrix":
        worlds = sorted({world for profile in checkpoint[key].values() for world in profile})
        values = [[float(checkpoint[key].get(agent, {}).get(world, 0.0)) for world in worlds] for agent in agents]
    else:
        worlds = sorted(checkpoint.get(key, {}))
        values = [[float(checkpoint[key].get(world, {}).get(agent, 0.0)) for world in worlds] for agent in agents]
    return agents, worlds, np.asarray(values, dtype=float)


def main() -> None:
    private_dir, shared_dir = _run_mock_pair()
    private = load_run(private_dir)
    shared = load_run(shared_dir)
    private_rows = checkpoint_rows(private)
    shared_rows = checkpoint_rows(shared)

    checkpoints = [row["checkpoint"] for row in private_rows]
    fig, ax = plt.subplots(figsize=(7, 4))
    for label, rows, color in (("PRIVATE (mock)", private_rows, "#2563eb"), ("SHARED (mock)", shared_rows, "#d97706")):
        ax.plot(checkpoints, [row["normalized_hse"] for row in rows], marker="o", label=label, color=color)
    ax.set(xlabel="checkpoint t", ylabel="normalized HSE", title="A · Behavioral diversity trajectory")
    ax.legend(frameon=False)
    _save(fig, "plot_A_normalized_hse.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    for label, rows, color in (("PRIVATE (mock)", private_rows, "#2563eb"), ("SHARED (mock)", shared_rows, "#d97706")):
        baseline = rows[0]["normalized_hse"]
        ax.plot(checkpoints, [row["normalized_hse"] - baseline for row in rows], marker="o", label=label, color=color)
    ax.axhline(0, color="#64748b", linewidth=1)
    ax.set(xlabel="checkpoint t", ylabel="Δ normalized HSE", title="B · Baseline-relative diversity")
    ax.legend(frameon=False)
    _save(fig, "plot_B_delta_hse.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    for label, rows, color in (("PRIVATE (mock)", private_rows, "#2563eb"), ("SHARED (mock)", shared_rows, "#d97706")):
        ax.plot(checkpoints, [row["phi"] for row in rows], marker="o", label=label, color=color)
    ax.set(xlabel="checkpoint t", ylabel="Φ(t)", title="C · Competence differentiation")
    ax.legend(frameon=False)
    _save(fig, "plot_C_phi.png")

    private_online = online_observables(private.events, num_agents=2)
    shared_online = online_observables(shared.events, num_agents=2)
    fig, ax = plt.subplots(figsize=(7, 4))
    for label, rows, color in (("PRIVATE (mock)", private_online, "#2563eb"), ("SHARED (mock)", shared_online, "#d97706")):
        ax.plot([row["round"] for row in rows], [row["normalized_utilization_entropy"] for row in rows], marker="o", label=label, color=color)
    ax.set(xlabel="interaction round", ylabel="normalized utilization entropy", title="D · Routing utilization")
    ax.legend(frameon=False)
    _save(fig, "plot_D_utilization_entropy.png")

    final_private = private.checkpoints[-1]
    final_shared = shared.checkpoints[-1]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for axis, label, checkpoint in zip(axes, ("PRIVATE (mock)", "SHARED (mock)"), (final_private, final_shared)):
        agents, worlds, values = _matrix(checkpoint, "competence_matrix")
        image = axis.imshow(values, vmin=0, vmax=1, cmap="Blues")
        axis.set(xticks=range(len(worlds)), xticklabels=worlds, yticks=range(len(agents)), yticklabels=agents, title=label)
        for row in range(values.shape[0]):
            for column in range(values.shape[1]):
                axis.text(column, row, f"{values[row, column]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=axes, shrink=0.8, label="accuracy")
    fig.suptitle("E · Competence heatmaps at final checkpoint")
    _save(fig, "plot_E_competence_heatmaps.png")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for axis, label, checkpoint in zip(axes, ("PRIVATE (mock)", "SHARED (mock)"), (final_private, final_shared)):
        agents, worlds, values = _matrix(checkpoint, "routing_counts_by_world_agent")
        row_sums = values.sum(axis=1, keepdims=True)
        values = np.divide(values, row_sums, out=np.zeros_like(values), where=row_sums > 0)
        image = axis.imshow(values, vmin=0, vmax=1, cmap="Oranges")
        axis.set(xticks=range(len(worlds)), xticklabels=worlds, yticks=range(len(agents)), yticklabels=agents, title=label)
        for row in range(values.shape[0]):
            for column in range(values.shape[1]):
                axis.text(column, row, f"{values[row, column]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=axes, shrink=0.8, label="routing proportion")
    fig.suptitle("F · Routing matrix by world")
    _save(fig, "plot_F_routing_heatmaps.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    for label, rows, color in (("PRIVATE (mock)", private_online, "#2563eb"), ("SHARED (mock)", shared_online, "#d97706")):
        route_entropy = [
            -sum(float(probability) * np.log2(float(probability)) for probability in row["routing_distribution"].values() if probability > 0)
            for row in rows
        ]
        ax.plot(route_entropy, [row["normalized_task_agent_mutual_information"] for row in rows], marker="o", label=label, color=color)
    ax.set(xlabel="H(R) over used labels", ylabel="normalized I(C;R)", title="G · Routing entropy and task-agent organization")
    ax.legend(frameon=False)
    _save(fig, "plot_G_routing_entropy_vs_mi.png")

    manifest = {
        "status": "MOCK DATA — NOT SCIENTIFIC RESULT",
        "backend": "mock",
        "conditions": {"private": private.run_id, "shared": shared.run_id},
        "probe_set": str(OUTPUT / "mock_probe_set.json"),
        "figures": sorted(path.name for path in OUTPUT.glob("plot_*.png")),
    }
    (OUTPUT / "mock_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT / "README.md").write_text(
        "# Mock readiness figures\n\n"
        "Every artifact in this directory is generated by `scripts/generate_mock_readiness.py` "
        "with the local deterministic MockBackend. **MOCK DATA — NOT SCIENTIFIC RESULT.**\n",
        encoding="utf-8",
    )
    print(f"Generated mock readiness artifacts in {OUTPUT}")


if __name__ == "__main__":
    main()

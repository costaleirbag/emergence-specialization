"""Tables and publication-quality plots used by generated notebooks.

This module belongs to the optional ``report`` dependency group. Scientific
metrics remain in the core package; these functions only reshape and present
already-recorded results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import Markdown
from matplotlib.colors import ListedColormap
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from .analysis import (
    RunBundle,
    behavioral_rows,
    candidate_rows,
    checkpoint_rows,
    combine_rows,
    competence_rows,
    distance_rows,
    final_metric_rows,
    individual_accuracy_rows,
    inference_rows,
    load_run,
    memory_rows,
    overview_record,
    round_rows,
    routing_rows,
    usage_summary,
)


METRIC_LABELS = {
    "normalized_hse": "Normalized HSE",
    "normalized_task_agent_mutual_information": "Normalized task–agent MI",
    "normalized_utilization_entropy": "Normalized utilization entropy",
    "oracle_gain": "Oracle gain",
    "oracle_society_accuracy": "Oracle society accuracy",
    "best_individual_accuracy": "Best individual accuracy",
}


def _configure_style() -> None:
    sns.set_theme(context="notebook", style="whitegrid", palette="colorblind")
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "axes.titleweight": "semibold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )


class _BaseReport:
    def __init__(self, report_dir: str | Path) -> None:
        _configure_style()
        self.report_dir = Path(report_dir).resolve()
        self.figures_dir = self.report_dir / "figures"
        self.tables_dir = self.report_dir / "tables"
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

    def save_figure(self, figure: plt.Figure, name: str) -> plt.Figure:
        figure.savefig(self.figures_dir / f"{name}.svg", bbox_inches="tight")
        figure.savefig(self.figures_dir / f"{name}.png", bbox_inches="tight")
        return figure

    def save_table(self, frame: pd.DataFrame, name: str) -> pd.DataFrame:
        frame.to_csv(self.tables_dir / f"{name}.csv", index=False)
        return frame


class RunReport(_BaseReport):
    def __init__(self, run_dir: str | Path, report_dir: str | Path) -> None:
        super().__init__(report_dir)
        self.bundle = load_run(run_dir)
        self.rounds = pd.DataFrame(round_rows(self.bundle))
        self.candidates = pd.DataFrame(candidate_rows(self.bundle))
        self.checkpoints = pd.DataFrame(checkpoint_rows(self.bundle))
        self.individual = pd.DataFrame(individual_accuracy_rows(self.bundle))
        self.competence = pd.DataFrame(competence_rows(self.bundle))
        self.routing = pd.DataFrame(routing_rows(self.bundle))
        self.behavior = pd.DataFrame(behavioral_rows(self.bundle))
        self.distances = pd.DataFrame(distance_rows(self.bundle))
        self.memory = pd.DataFrame(memory_rows(self.bundle))
        self.inferences = pd.DataFrame(inference_rows(self.bundle))

    def title(self) -> Markdown:
        return Markdown(
            f"# Emergent Specialization — run report\n\n"
            f"**Run:** `{self.bundle.run_id}`  \n"
            f"**Condition:** `{self.bundle.condition}` · **Seed:** `{self.bundle.seed}` · "
            f"**Backend:** `{self.bundle.backend_name}`"
        )

    def methodological_notice(self) -> Markdown:
        if self.bundle.is_mock:
            return Markdown(
                "> **Mock run.** This report validates the harness and analysis pipeline only. "
                "Do not interpret its behavioral patterns as evidence about DeepSeek or emergent specialization."
            )
        return Markdown(
            "> **Interpretation guardrail.** HSE measures behavioral difference, not usefulness. "
            "Read it together with task–agent MI, utilization, complementarity, temporal stability, "
            "the shared-memory control, and repeated seeds."
        )

    def overview(self) -> pd.DataFrame:
        record = overview_record(self.bundle)
        frame = pd.DataFrame(
            [{"field": key.replace("_", " ").title(), "value": value} for key, value in record.items()]
        )
        return self.save_table(frame, "run-overview")

    def usage(self) -> pd.DataFrame:
        summary = usage_summary(self.bundle)
        frame = pd.DataFrame(
            [{"field": key.replace("_", " ").title(), "value": value} for key, value in summary.items()]
        )
        return self.save_table(frame, "usage-summary")

    def export_tables(self) -> pd.DataFrame:
        usage_frame = self.usage()
        tables = {
            "rounds": self.rounds,
            "candidates": self.candidates,
            "checkpoint-metrics": self.checkpoints,
            "individual-accuracy": self.individual,
            "competence": self.competence,
            "routing": self.routing,
            "behavioral-vectors": self.behavior,
            "behavioral-distances": self.distances,
            "memory": self.memory,
            "inferences": self.inferences,
            "usage-summary": usage_frame,
        }
        records = []
        for name, frame in tables.items():
            self.save_table(frame, name)
            records.append({"table": name, "rows": len(frame), "columns": len(frame.columns)})
        return pd.DataFrame(records)

    def plot_society_metrics(self) -> plt.Figure:
        metrics = [
            "normalized_hse",
            "normalized_task_agent_mutual_information",
            "normalized_utilization_entropy",
            "oracle_gain",
        ]
        figure, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
        for axis, metric in zip(axes.flat, metrics):
            axis.plot(self.checkpoints["checkpoint"], self.checkpoints[metric], marker="o", linewidth=2)
            axis.set_title(METRIC_LABELS[metric])
            axis.set_xlabel("Interaction round")
            axis.set_ylabel("Value")
            axis.set_ylim(-0.03, 1.03)
        figure.suptitle("Society-level metrics through time", fontsize=15)
        figure.tight_layout()
        return self.save_figure(figure, "society-metrics")

    def plot_individual_accuracy(self) -> plt.Figure:
        figure, axis = plt.subplots(figsize=(10, 4.8))
        sns.lineplot(
            data=self.individual,
            x="checkpoint",
            y="accuracy",
            hue="agent_id",
            marker="o",
            linewidth=2,
            ax=axis,
        )
        axis.set(title="Individual probe accuracy", xlabel="Interaction round", ylabel="Accuracy", ylim=(-0.03, 1.03))
        figure.tight_layout()
        return self.save_figure(figure, "individual-accuracy")

    def plot_competence(self) -> plt.Figure:
        checkpoints = [int(self.competence["checkpoint"].min()), int(self.competence["checkpoint"].max())]
        checkpoints = list(dict.fromkeys(checkpoints))
        figure, axes = plt.subplots(1, len(checkpoints), figsize=(6 * len(checkpoints), 4.5), squeeze=False)
        for axis, checkpoint in zip(axes.flat, checkpoints):
            frame = self.competence[self.competence["checkpoint"] == checkpoint]
            matrix = frame.pivot(index="agent_id", columns="world", values="accuracy")
            sns.heatmap(matrix, annot=True, fmt=".2f", vmin=0, vmax=1, cmap="viridis", ax=axis)
            axis.set_title(f"Per-domain competence — t={checkpoint}")
            axis.set_xlabel("World")
            axis.set_ylabel("Agent")
        figure.tight_layout()
        return self.save_figure(figure, "competence-heatmaps")

    def plot_routing(self) -> plt.Figure:
        final_checkpoint = int(self.routing["checkpoint"].max())
        final = self.routing[self.routing["checkpoint"] == final_checkpoint]
        matrix = final.pivot(index="world", columns="agent_id", values="proportion")
        figure, axis = plt.subplots(figsize=(8, 4.8))
        sns.heatmap(matrix, annot=True, fmt=".2f", vmin=0, vmax=1, cmap="mako", ax=axis)
        axis.set_title(f"Routing distribution by world — cumulative through t={final_checkpoint}")
        axis.set_xlabel("Selected agent")
        axis.set_ylabel("World")
        figure.tight_layout()
        return self.save_figure(figure, "routing-heatmap")

    def plot_memory(self) -> plt.Figure:
        figure, axis = plt.subplots(figsize=(10, 4.8))
        sns.lineplot(
            data=self.memory,
            x="round",
            y="memory_count",
            hue="agent_id",
            marker="o" if self.memory["round"].nunique() <= 25 else None,
            linewidth=2,
            ax=axis,
        )
        axis.set(title="Controlled memory accumulation", xlabel="Interaction round", ylabel="Stored experiences")
        figure.tight_layout()
        return self.save_figure(figure, "memory-growth")

    def plot_round_dynamics(self) -> plt.Figure:
        figure, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, height_ratios=(1.15, 1))
        worlds = list(dict.fromkeys(self.rounds["world"].tolist()))
        world_index = {world: index for index, world in enumerate(worlds)}
        agents = list(self.bundle.agent_ids)
        palette = dict(zip(agents, sns.color_palette("colorblind", n_colors=len(agents))))
        for agent in agents:
            selected = self.rounds[self.rounds["selected_agent"] == agent]
            axes[0].scatter(
                selected["round"],
                selected["world"].map(world_index),
                label=agent,
                color=palette[agent],
                s=48,
                alpha=0.85,
            )
        axes[0].set_yticks(range(len(worlds)), worlds)
        axes[0].set(title="Routing decisions by round and world", ylabel="World")
        axes[0].legend(ncol=min(4, len(agents)), loc="upper center", bbox_to_anchor=(0.5, 1.24))

        correctness = self.rounds["selected_correct"].astype(float)
        window = max(2, min(10, len(correctness)))
        axes[1].step(self.rounds["round"], correctness, where="mid", alpha=0.3, label="Selected answer")
        axes[1].plot(
            self.rounds["round"], correctness.rolling(window, min_periods=1).mean(), linewidth=2.2, label=f"Rolling mean ({window})"
        )
        axes[1].set(xlabel="Interaction round", ylabel="Correctness", ylim=(-0.05, 1.05))
        axes[1].legend(loc="lower right")
        figure.tight_layout()
        return self.save_figure(figure, "round-dynamics")

    def plot_confidence(self) -> plt.Figure:
        valid = self.candidates.dropna(subset=["confidence"])
        figure, axes = plt.subplots(1, 2, figsize=(12, 4.6))
        sns.lineplot(
            data=valid,
            x="round",
            y="confidence",
            hue="agent_id",
            linewidth=1.6,
            alpha=0.8,
            ax=axes[0],
        )
        axes[0].set(title="Stated confidence by agent", xlabel="Interaction round", ylabel="Confidence", ylim=(-0.03, 1.03))
        sns.boxplot(data=valid, x="selected", y="confidence", hue="correct", ax=axes[1])
        axes[1].set(title="Confidence by selection and correctness", xlabel="Selected by router", ylabel="Confidence", ylim=(-0.03, 1.03))
        figure.tight_layout()
        return self.save_figure(figure, "confidence-diagnostics")

    def plot_probe_behavior(self) -> plt.Figure:
        final_checkpoint = int(self.behavior["checkpoint"].max())
        final = self.behavior[self.behavior["checkpoint"] == final_checkpoint]
        matrix = final.pivot(index="agent_id", columns="probe_index", values="success")
        figure, axis = plt.subplots(figsize=(14, 3.4))
        sns.heatmap(
            matrix,
            vmin=0,
            vmax=1,
            cmap=ListedColormap(["#eeeeee", "#237a57"]),
            cbar=False,
            linewidths=0.15,
            ax=axis,
        )
        axis.set(title=f"Probe success/failure raster — t={final_checkpoint}", xlabel="Probe index", ylabel="Agent")
        figure.tight_layout()
        return self.save_figure(figure, "probe-behavior-raster")

    def plot_behavioral_structure(self) -> plt.Figure:
        final_checkpoint = int(self.distances["checkpoint"].max())
        final = self.distances[self.distances["checkpoint"] == final_checkpoint]
        matrix = final.pivot(index="agent_left", columns="agent_right", values="distance")
        labels = matrix.index.tolist()
        values = matrix.to_numpy(dtype=float)
        figure, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})
        sns.heatmap(matrix, annot=True, fmt=".2f", vmin=0, vmax=1, cmap="rocket", ax=axes[0])
        axes[0].set(title=f"Behavioral cosine distance — t={final_checkpoint}", xlabel="Agent", ylabel="Agent")
        if len(labels) > 1:
            condensed = squareform(values, checks=False)
            linkage_matrix = linkage(condensed, method="single")
            dendrogram(linkage_matrix, labels=labels, ax=axes[1], color_threshold=None)
            axes[1].set(title="Single-linkage behavioral dendrogram", xlabel="Agent", ylabel="Cosine distance", ylim=(-0.03, 1.03))
        else:
            axes[1].text(0.5, 0.5, "One agent; dendrogram unavailable", ha="center", va="center")
            axes[1].set_axis_off()
        figure.tight_layout()
        return self.save_figure(figure, "behavioral-structure")

    def inference_health(self) -> pd.DataFrame:
        if self.inferences.empty:
            return pd.DataFrame()
        frame = self.inferences.copy()
        frame["has_error"] = frame["error"].notna()
        summary = (
            frame.groupby("phase", dropna=False)
            .agg(
                calls=("agent_id", "size"),
                errors=("has_error", "sum"),
                retries=("attempt", lambda values: int((pd.Series(values).fillna(0) > 0).sum())),
                median_latency_s=("latency_s", "median"),
                p95_latency_s=("latency_s", lambda values: pd.Series(values).dropna().quantile(0.95)),
                total_tokens=("total_tokens", lambda values: values.sum(min_count=1)),
            )
            .reset_index()
        )
        return self.save_table(summary, "inference-health")

    def plot_inference_health(self) -> plt.Figure:
        valid = self.inferences.dropna(subset=["latency_s"]).copy()
        figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))
        if valid.empty:
            for axis in axes:
                axis.text(0.5, 0.5, "No latency data", ha="center", va="center")
                axis.set_axis_off()
        else:
            sns.boxplot(data=valid, x="phase", y="latency_s", ax=axes[0])
            axes[0].set(title="Inference latency distribution", xlabel="Phase", ylabel="Latency (seconds)")
            error_counts = (
                self.inferences.assign(status=np.where(self.inferences["error"].notna(), "error", "valid"))
                .groupby(["phase", "status"])
                .size()
                .reset_index(name="count")
            )
            sns.barplot(data=error_counts, x="phase", y="count", hue="status", ax=axes[1])
            axes[1].set(title="Valid and failed inference attempts", xlabel="Phase", ylabel="Attempts")
        figure.tight_layout()
        return self.save_figure(figure, "inference-health")


class ComparisonReport(_BaseReport):
    def __init__(self, run_dirs: Sequence[str | Path], report_dir: str | Path) -> None:
        super().__init__(report_dir)
        if len(run_dirs) < 2:
            raise ValueError("A comparison report requires at least two runs")
        self.bundles = [load_run(path) for path in run_dirs]
        self.checkpoints = pd.DataFrame(combine_rows(self.bundles, checkpoint_rows))
        self.final_metrics = pd.DataFrame(final_metric_rows(self.bundles))
        self.overviews = pd.DataFrame([overview_record(bundle) for bundle in self.bundles])

    def title(self) -> Markdown:
        conditions = ", ".join(sorted({bundle.condition for bundle in self.bundles}))
        return Markdown(
            f"# Emergent Specialization — comparison report\n\n"
            f"**Runs:** {len(self.bundles)} · **Conditions:** {conditions} · "
            f"**Seeds:** {', '.join(str(seed) for seed in sorted({bundle.seed for bundle in self.bundles if bundle.seed is not None}))}"
        )

    def methodological_notice(self) -> Markdown:
        mock_count = sum(bundle.is_mock for bundle in self.bundles)
        mock_note = (
            f" {mock_count} run(s) use the mock backend and must not be interpreted as model evidence."
            if mock_count
            else ""
        )
        return Markdown(
            "> **Cross-run guardrail.** Agent labels are exchangeable across seeds. The main "
            "comparison therefore emphasizes permutation-invariant metrics and does not average "
            f"raw agent heatmaps without alignment.{mock_note}"
        )

    def overview(self) -> pd.DataFrame:
        return self.save_table(self.overviews, "comparison-overview")

    def export_tables(self) -> pd.DataFrame:
        self.save_table(self.checkpoints, "checkpoint-metrics")
        self.save_table(self.final_metrics, "final-metrics")
        return pd.DataFrame(
            [
                {"table": "comparison-overview", "rows": len(self.overviews)},
                {"table": "checkpoint-metrics", "rows": len(self.checkpoints)},
                {"table": "final-metrics", "rows": len(self.final_metrics)},
            ]
        )

    def plot_metric_trajectories(self) -> plt.Figure:
        metrics = [
            "normalized_hse",
            "normalized_task_agent_mutual_information",
            "normalized_utilization_entropy",
            "oracle_gain",
        ]
        figure, axes = plt.subplots(2, 2, figsize=(12, 7.5), sharex=True)
        palette = dict(
            zip(sorted(self.checkpoints["condition"].unique()), sns.color_palette("colorblind", n_colors=self.checkpoints["condition"].nunique()))
        )
        for axis, metric in zip(axes.flat, metrics):
            for run_id, frame in self.checkpoints.groupby("run_id"):
                condition = str(frame["condition"].iloc[0])
                axis.plot(frame["checkpoint"], frame[metric], color=palette[condition], alpha=0.28, linewidth=1.2)
            mean = self.checkpoints.groupby(["condition", "checkpoint"], as_index=False)[metric].mean()
            for condition, frame in mean.groupby("condition"):
                axis.plot(
                    frame["checkpoint"], frame[metric], color=palette[str(condition)], marker="o", linewidth=2.6, label=str(condition)
                )
            axis.set(title=METRIC_LABELS[metric], xlabel="Interaction round", ylabel="Value", ylim=(-0.03, 1.03))
        axes[0, 0].legend(title="Condition")
        figure.suptitle("Private/shared trajectories (thin lines: runs; thick lines: condition means)", fontsize=14)
        figure.tight_layout()
        return self.save_figure(figure, "comparison-trajectories")

    def plot_final_metrics(self) -> plt.Figure:
        metrics = list(METRIC_LABELS)
        frame = self.final_metrics[self.final_metrics["metric"].isin(metrics)].copy()
        figure, axes = plt.subplots(2, 3, figsize=(14, 7.5))
        for axis, metric in zip(axes.flat, metrics):
            subset = frame[frame["metric"] == metric]
            sns.stripplot(data=subset, x="condition", y="value", hue="condition", jitter=0.08, size=7, ax=axis)
            means = subset.groupby("condition", as_index=False)["value"].mean()
            sns.pointplot(data=means, x="condition", y="value", color="black", markers="D", linestyles="none", ax=axis)
            legend = axis.get_legend()
            if legend is not None:
                legend.remove()
            axis.set(title=METRIC_LABELS[metric], xlabel="Condition", ylabel="Final value", ylim=(-0.03, 1.03))
        figure.suptitle("Final checkpoint metrics across runs", fontsize=14)
        figure.tight_layout()
        return self.save_figure(figure, "final-metric-comparison")

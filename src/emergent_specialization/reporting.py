"""Generate executed Jupyter notebooks and standalone HTML reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable, Sequence

from .analysis import RunBundle, load_run, sha256_file


def _report_dependencies() -> tuple[Any, Any, Any]:
    try:
        import nbformat
        from nbclient import NotebookClient
        from nbconvert import HTMLExporter
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise RuntimeError(
            "Report dependencies are not installed. Run `uv sync --group report` "
            "or prefix the command with `uv run --group report`."
        ) from exc
    return nbformat, NotebookClient, HTMLExporter


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _code_cell(source: str) -> dict[str, Any]:
    nbformat, _, _ = _report_dependencies()
    return nbformat.v4.new_code_cell(source, metadata={"tags": ["report-cell"]})


def _markdown_cell(source: str) -> dict[str, Any]:
    nbformat, _, _ = _report_dependencies()
    return nbformat.v4.new_markdown_cell(source)


def _figure_cell(method: str) -> dict[str, Any]:
    return _code_cell(f"fig = report.{method}()\ndisplay(fig)\nplt.close(fig)")


def build_run_notebook(run_dir: Path, report_dir: Path) -> Any:
    nbformat, _, _ = _report_dependencies()
    cells = [
        _code_cell(
            "from IPython.display import display\n"
            "import matplotlib.pyplot as plt\n"
            "from emergent_specialization.report_runtime import RunReport\n\n"
            f"RUN_DIR = {str(run_dir)!r}\n"
            f"REPORT_DIR = {str(report_dir)!r}\n"
            "report = RunReport(RUN_DIR, REPORT_DIR)\n"
            "display(report.title())\n"
            "display(report.methodological_notice())"
        ),
        _markdown_cell("## Provenance and run summary"),
        _code_cell("display(report.overview())"),
        _markdown_cell(
            "## Society-level trajectories\n\n"
            "These metrics separate behavioral difference (HSE), organization (task–agent MI), "
            "routing collapse (utilization entropy), and useful complementarity (oracle gain)."
        ),
        _figure_cell("plot_society_metrics"),
        _markdown_cell("## Individual and domain competence"),
        _figure_cell("plot_individual_accuracy"),
        _figure_cell("plot_competence"),
        _markdown_cell("## Routing and memory dynamics"),
        _figure_cell("plot_routing"),
        _figure_cell("plot_memory"),
        _figure_cell("plot_round_dynamics"),
        _markdown_cell(
            "## Confidence diagnostics\n\n"
            "Confidence is treated as a routing mechanism, not as a calibrated probability."
        ),
        _figure_cell("plot_confidence"),
        _markdown_cell("## Behavioral structure on the fixed probe set"),
        _figure_cell("plot_probe_behavior"),
        _figure_cell("plot_behavioral_structure"),
        _markdown_cell("## Inference health and auditability"),
        _code_cell("display(report.inference_health())"),
        _figure_cell("plot_inference_health"),
        _markdown_cell("## Exported analysis tables"),
        _code_cell("display(report.export_tables())"),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.update(
        {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "emergent_specialization": {"report_type": "single_run", "run_dir": str(run_dir)},
        }
    )
    return notebook


def build_comparison_notebook(run_dirs: Sequence[Path], report_dir: Path) -> Any:
    nbformat, _, _ = _report_dependencies()
    cells = [
        _code_cell(
            "from IPython.display import display\n"
            "import matplotlib.pyplot as plt\n"
            "from emergent_specialization.report_runtime import ComparisonReport\n\n"
            f"RUN_DIRS = {[str(path) for path in run_dirs]!r}\n"
            f"REPORT_DIR = {str(report_dir)!r}\n"
            "report = ComparisonReport(RUN_DIRS, REPORT_DIR)\n"
            "display(report.title())\n"
            "display(report.methodological_notice())"
        ),
        _markdown_cell("## Runs included in this comparison"),
        _code_cell("display(report.overview())"),
        _markdown_cell("## Metric trajectories by condition and seed"),
        _figure_cell("plot_metric_trajectories"),
        _markdown_cell("## Final checkpoint comparison"),
        _figure_cell("plot_final_metrics"),
        _markdown_cell("## Exported comparison tables"),
        _code_cell("display(report.export_tables())"),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.update(
        {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "emergent_specialization": {
                "report_type": "comparison",
                "run_dirs": [str(path) for path in run_dirs],
            },
        }
    )
    return notebook


def _execute_and_export(notebook: Any, report_dir: Path) -> tuple[Path, Path]:
    nbformat, NotebookClient, HTMLExporter = _report_dependencies()
    report_dir.mkdir(parents=True, exist_ok=True)
    notebook_path = report_dir / "report.ipynb"
    html_path = report_dir / "report.html"
    nbformat.write(notebook, notebook_path)
    client = NotebookClient(notebook, timeout=1200, kernel_name="python3", allow_errors=False)
    executed = client.execute(cwd=str(_project_root()))
    nbformat.write(executed, notebook_path)
    exporter = HTMLExporter(
        template_name="lab",
        exclude_input=True,
        exclude_input_prompt=True,
        exclude_output_prompt=True,
    )
    body, _ = exporter.from_notebook_node(executed)
    html_path.write_text(body, encoding="utf-8")
    return notebook_path, html_path


def _runtime_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in ("emergent-specialization", "matplotlib", "nbclient", "nbconvert", "numpy", "pandas", "seaborn", "scipy"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _artifact_hashes(report_dir: Path) -> dict[str, str]:
    return {
        str(path.relative_to(report_dir)): sha256_file(path)
        for path in sorted(report_dir.rglob("*"))
        if path.is_file() and path.name != "report-manifest.json"
    }


def _write_manifest(report_dir: Path, payload: dict[str, Any]) -> Path:
    manifest_path = report_dir / "report-manifest.json"
    manifest = {
        "format": "emergent-specialization-report-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "runtime_versions": _runtime_versions(),
        **payload,
        "artifact_sha256": _artifact_hashes(report_dir),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def generate_run_report(run_dir: str | Path, output_dir: str | Path | None = None) -> Path:
    bundle: RunBundle = load_run(run_dir)
    destination = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else (_project_root() / "reports" / bundle.run_id).resolve()
    )
    notebook = build_run_notebook(bundle.run_dir, destination)
    _execute_and_export(notebook, destination)
    _write_manifest(
        destination,
        {
            "report_type": "single_run",
            "run_id": bundle.run_id,
            "run_dir": str(bundle.run_dir),
            "input_sha256": bundle.input_hashes,
        },
    )
    return destination


def generate_comparison_report(
    run_dirs: Sequence[str | Path], output_dir: str | Path | None = None
) -> Path:
    bundles = [load_run(path) for path in run_dirs]
    if len(bundles) < 2:
        raise ValueError("A comparison report requires at least two completed runs")
    if output_dir is None:
        digest = hashlib.sha256("\n".join(bundle.run_id for bundle in bundles).encode()).hexdigest()[:10]
        destination = (_project_root() / "reports" / f"comparison-{digest}").resolve()
    else:
        destination = Path(output_dir).expanduser().resolve()
    notebook = build_comparison_notebook([bundle.run_dir for bundle in bundles], destination)
    _execute_and_export(notebook, destination)
    _write_manifest(
        destination,
        {
            "report_type": "comparison",
            "runs": [
                {"run_id": bundle.run_id, "run_dir": str(bundle.run_dir), "input_sha256": bundle.input_hashes}
                for bundle in bundles
            ],
        },
    )
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an executed notebook and HTML report for one run.")
    parser.add_argument("--run", required=True, help="Completed data/runs/<run-id> directory")
    parser.add_argument("--output", help="Report output directory; defaults to reports/<run-id>")
    return parser


def build_comparison_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare completed runs in an executed notebook and HTML report.")
    parser.add_argument("--runs", nargs="+", required=True, help="Two or more completed run directories")
    parser.add_argument("--output", help="Report output directory")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    destination = generate_run_report(args.run, args.output)
    print(f"Executed notebook: {destination / 'report.ipynb'}")
    print(f"HTML report: {destination / 'report.html'}")
    print(f"Figures and tables: {destination}")


def comparison_main(argv: Iterable[str] | None = None) -> None:
    args = build_comparison_parser().parse_args(list(argv) if argv is not None else None)
    destination = generate_comparison_report(args.runs, args.output)
    print(f"Executed comparison notebook: {destination / 'report.ipynb'}")
    print(f"HTML comparison report: {destination / 'report.html'}")


if __name__ == "__main__":
    main()

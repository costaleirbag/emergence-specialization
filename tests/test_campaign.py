from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from emergent_specialization.campaign import (
    GATE_1,
    GATE_2,
    GATE_RANDOM_10,
    HARD_COST_CAP_USD,
    CampaignRun,
    _apply_reuse,
    _forecast,
    _gate_summary,
    approve_gate,
    build_campaign_plan,
    build_random_gate_plan,
    generate_gate_report,
    observed_baseline_cost_per_logical,
    run_gate,
)
from emergent_specialization.batch import nominal_call_counts
from emergent_specialization.config import load_config
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.probes import generate_probe_payload, write_probe_set


REPO_ROOT = Path(__file__).resolve().parents[1]
HAS_HISTORICAL_BASELINE = any((REPO_ROOT / "data" / "runs").glob("**/summary.json"))


class CampaignPlanningTests(unittest.TestCase):
    def test_plan_has_registered_stage_sizes_and_call_counts(self) -> None:
        rows = build_campaign_plan()
        self.assertEqual(len(rows), 320)
        self.assertEqual(sum(row.stage == "A" for row in rows), 200)
        self.assertEqual(sum(row.stage == "B" for row in rows), 100)
        self.assertEqual(sum(row.stage == "C" for row in rows), 20)
        self.assertEqual({row.nominal_calls for row in rows if row.stage in {"A", "B"}}, {560})
        self.assertEqual({row.nominal_calls for row in rows if row.stage == "C"}, {2160})
        self.assertEqual({row.probe_set_hash for row in rows}, {"cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e"})

    @unittest.skipUnless(HAS_HISTORICAL_BASELINE, "requires local historical baseline runs")
    def test_existing_seed_one_pair_is_reused_without_changing_plan(self) -> None:
        rows, reused = _apply_reuse(build_campaign_plan())
        self.assertEqual(len(reused), 2)
        self.assertEqual(sum(row.status == "reused" for row in rows), 2)
        self.assertEqual({row.seed for row in rows if row.status == "reused"}, {1})

    @unittest.skipUnless(HAS_HISTORICAL_BASELINE, "requires local historical baseline runs")
    def test_forecast_is_hard_cap_aware(self) -> None:
        rows, _ = _apply_reuse(build_campaign_plan())
        per_logical = observed_baseline_cost_per_logical()
        forecast = _forecast(rows, per_logical)
        self.assertEqual(forecast["new_runs"], 318)
        self.assertGreater(float(forecast["projected_cost_usd"]), HARD_COST_CAP_USD)

    @unittest.skipUnless(HAS_HISTORICAL_BASELINE, "requires local historical baseline runs")
    def test_gate_one_is_small_and_gate_two_is_locked(self) -> None:
        rows, _ = _apply_reuse(build_campaign_plan())
        gate_one = [row for row in rows if row.gate == GATE_1]
        self.assertEqual({row.seed for row in gate_one}, set(range(1, 11)))
        self.assertEqual(sum(row.status != "reused" for row in gate_one), 18)
        summary = _gate_summary(rows, GATE_1, observed_baseline_cost_per_logical())
        self.assertEqual(summary["new_runs"], 18)
        self.assertLess(float(summary["expected_nominal_cost_usd"]), 1.0)

    def test_random_gate_plan_is_ten_paired_seeds_and_11200_calls(self) -> None:
        rows = build_random_gate_plan()
        self.assertEqual(len(rows), 20)
        self.assertEqual({row.seed for row in rows}, set(range(1, 11)))
        self.assertEqual({row.condition for row in rows}, {"private", "shared"})
        self.assertEqual({row.gate for row in rows}, {GATE_RANDOM_10})
        self.assertEqual({row.router for row in rows}, {"random"})
        self.assertEqual(sum(row.nominal_calls for row in rows), 11_200)
        self.assertEqual(sum(row.max_physical_calls for row in rows), 14_000)

    def test_mock_gate_lifecycle_resume_report_and_human_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probes = root / "probes.json"
            write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
            private_config_path = root / "private.yaml"
            private_config_path.write_text(
                "experiment:\n  num_agents: 2\n  num_rounds: 2\n  checkpoints: [0, 2]\n  technical_retries: 0\n  console_summary: false\n"
                "agent:\n  backend: deepseek_direct\n  model: deepseek-v4-flash\n  thinking: 'off'\n"
                "router:\n  strategy: confidence\n  epsilon: 0.0\ncondition:\n  memory_mode: private\n"
                f"logging:\n  output_dir: {root / 'runs'}\n  probe_set_path: {probes}\n",
                encoding="utf-8",
            )
            shared_config_path = root / "shared.yaml"
            shared_config_path.write_text(private_config_path.read_text(encoding="utf-8").replace("memory_mode: private", "memory_mode: shared"), encoding="utf-8")
            config = load_config(private_config_path)
            probe_tasks, probe_hash = __import__("emergent_specialization.probes", fromlist=["load_probe_set"]).load_probe_set(probes)
            counts = nominal_call_counts(config, len(probe_tasks))
            rows: list[dict[str, object]] = []
            for seed in (97, 98):
                for condition in ("private", "shared"):
                    config_path = private_config_path if condition == "private" else shared_config_path
                    row = CampaignRun(
                        stage="A", seed=seed, condition=condition, router="confidence",
                        config_path=str(config_path), config_hash=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                        probe_set_hash=probe_hash, nominal_calls=counts["nominal_calls"],
                        max_physical_calls=counts["max_physical_calls"], interaction_calls=counts["interaction_calls"],
                        probe_calls=counts["probe_calls"], gate=GATE_1, identity=f"test:{seed}:{condition}",
                    )
                    rows.append(asdict(row))
            manifest = {
                "campaign": "test", "gates": {GATE_1: {"status": "planned", "hard_budget_usd": 1.0}, GATE_2: {"status": "locked"}},
                "state": {"status": "gate_1_planned"}, "runs": rows,
            }
            manifest_file = root / "manifest.json"
            run_root = root / "runs"
            self.assertEqual(run_gate(manifest, GATE_1, max_new_pairs=1, mock=True, manifest_file=manifest_file, run_root=run_root), 0)
            first_calls = [row["status"] for row in rows if row["seed"] == 97]
            self.assertEqual(first_calls, ["completed", "completed"])
            self.assertEqual(run_gate(manifest, GATE_1, max_new_pairs=1, mock=True, manifest_file=manifest_file, run_root=run_root), 0)
            self.assertEqual([row["status"] for row in rows], ["completed"] * 4)
            report = generate_gate_report(manifest, GATE_1, output_dir=root / "report" / "gate-1")
            self.assertTrue(report.exists())
            interim = json.loads((root / "report" / "gate-1" / "interim_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(interim["data_quality"]["completed_paired_seeds"], 2)
            self.assertEqual(manifest["gates"][GATE_2]["status"], "locked")
            manifest["gates"][GATE_1]["status"] = "complete"
            approve_gate(manifest, GATE_2, 2.0, manifest_file=manifest_file, report_dir=root / "report" / "gate-1")
            self.assertEqual(manifest["gates"][GATE_2]["status"], "approved")

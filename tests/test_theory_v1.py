import unittest

import numpy as np

from emergent_specialization.theory_v1.dynamics import (
    centered_projector,
    classify_regime,
    competence_interaction,
    critical_beta,
    jacobian,
    psi_spec,
    retention,
    spectral_summary,
    transfer_operator,
)
from emergent_specialization.theory_v1.ecologies import AffineBooleanV1, V31Fresh, fresh_training_state
from emergent_specialization.theory_v1.micro_design import expected_call_counts, macro_cells, micro_manifest
from emergent_specialization.theory_v1.micro_estimation import estimate_k_explicit, estimate_k_pairwise, superposition_diagnostics
from emergent_specialization.theory_v1.prediction import predictions_for_k
from emergent_specialization.theory_v1.scoring import kendall_tau, pairwise_concordance, spearman
from emergent_specialization.theory_v1.scorecard import full_scorecard, score_t7_criticality, score_t9_mode
from emergent_specialization.theory_v1.micro_runner import build_tasks, render_user
from emergent_specialization.theory_v1.macro_runner import expected_calls as macro_expected_calls, run_mock_protocol


class TheoryV1Tests(unittest.TestCase):
    def test_centering(self):
        for size in (2, 4, 7):
            projector = centered_projector(size)
            self.assertTrue(np.allclose(projector @ np.ones(size), 0.0))

    def test_psi_removes_main_effects(self):
        constant = np.ones((4, 4))
        row_only = np.arange(4.0)[:, None] + np.zeros((4, 4))
        col_only = np.zeros((4, 4)) + np.arange(4.0)[None, :]
        specialist = np.eye(4)
        self.assertAlmostEqual(psi_spec(constant), 0.0)
        self.assertAlmostEqual(psi_spec(row_only), 0.0)
        self.assertAlmostEqual(psi_spec(col_only), 0.0)
        self.assertGreater(psi_spec(specialist), 0.0)
        self.assertAlmostEqual(psi_spec(specialist[[2, 0, 3, 1]][:, [1, 3, 0, 2]]), psi_spec(specialist))

    def test_retention_and_sharing(self):
        self.assertAlmostEqual(retention(8, 0.0), 1.0 - (1 / 4) / 8)
        self.assertAlmostEqual(retention(8, 1.0), 1.0 - 1 / 8)
        k = np.eye(4)
        self.assertTrue(np.allclose(jacobian(k, 8, 1.0, 12.0, .1), retention(8, 1.0) * np.eye(4)))

    def test_matched_gain_is_identical(self):
        k = np.eye(4) - np.ones((4, 4)) / 4
        left = jacobian(k, 8, 0.0, 8.0, .10)
        right = jacobian(k, 8, 0.0, 16.0, .55)
        self.assertTrue(np.allclose(left, right))

    def test_k_estimators_recover_known_operator(self):
        known = np.array([[.8, .1, .0, .1], [.1, .8, .1, .0], [.0, .1, .8, .1], [.1, .0, .1, .8]])
        projector = centered_projector(4)
        known = projector @ known @ projector
        swaps, responses = [], []
        for source in range(4):
            for target in range(4):
                if source == target:
                    continue
                delta = np.eye(4)[target] - np.eye(4)[source]
                swaps.append(delta); responses.append(delta @ known)
        self.assertTrue(np.allclose(estimate_k_explicit(swaps, responses), known, atol=1e-10))
        self.assertTrue(np.allclose(estimate_k_pairwise(swaps, responses), known, atol=1e-10))

    def test_superposition_fixture(self):
        observed = [[1, 2, 3], [2, 4, 6]]
        self.assertAlmostEqual(superposition_diagnostics(observed, observed)["r2"], 1.0)

    def test_ecology_b_is_binary_and_nonconstant(self):
        for niche in range(4):
            values = {AffineBooleanV1.solve(83101, niche, x) for x in __import__("itertools").product((0, 1), repeat=6)}
            self.assertGreater(len(values), 1)
        self.assertEqual(len(fresh_training_state("V31_FRESH", 73101, 8)), 8)

    def test_call_counts_and_manifest(self):
        counts = expected_call_counts()
        self.assertEqual(counts["micro"], 26112)
        self.assertEqual(counts["macro"], 186368)
        self.assertEqual(counts["total"], 212480)
        manifest = micro_manifest()
        self.assertEqual(len(manifest["units"]), 48)
        self.assertEqual(len(macro_cells()), 18)

    def test_prediction_and_regime_fixtures(self):
        rows = predictions_for_k(np.eye(4), 8)
        self.assertEqual(len(rows), 18)
        self.assertEqual(rows[0]["regime"], "SUBCRITICAL")
        self.assertIn(classify_regime(1.1), {"SUPERCRITICAL"})
        self.assertIsNone(critical_beta(np.eye(4), 8, 1.0, .1))
        self.assertIn("dominant_mode", spectral_summary(transfer_operator(np.eye(4))))

    def test_rank_score_helpers(self):
        self.assertAlmostEqual(spearman([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertAlmostEqual(kendall_tau([1, 2, 3], [2, 4, 6]), 1.0)
        result = pairwise_concordance([0, .1, .2] * 4, [0, .1, .2] * 4, margin=.01)
        self.assertEqual(result["status"], "PASS")

    def test_scorecard_is_explicitly_not_run_without_observations(self):
        scorecard = full_scorecard()
        self.assertEqual(scorecard["overall"], "NOT_RUN")
        self.assertEqual(scorecard["T1"]["status"], "NOT_RUN")
        self.assertEqual(score_t7_criticality([], []), {"test": "T7", "status": "NOT_RUN", "reason": "no confirmatory observations"})
        self.assertEqual(score_t9_mode([])["status"], "NON_IDENTIFIABLE")

    def test_micro_runner_builds_exact_frozen_context_count(self):
        tasks = build_tasks()
        self.assertEqual(len(tasks), 26112)
        self.assertEqual(len({task["logical_id"] for task in tasks}), 26112)
        prompt_hashes = {task["prompt_hash"] for task in tasks}
        self.assertGreater(len(prompt_hashes), 1)
        self.assertLessEqual(len(prompt_hashes), len(tasks))
        self.assertTrue(all(task["prompt_hash"] for task in tasks))

    def test_micro_runner_uses_held_out_probes_and_feedback_only_memory(self):
        task = next(task for task in build_tasks() if task["ecology"] == "V31_FRESH" and task["k"] == 8)
        memory_xs = {tuple(item["x"]) for item in task["memory"]}
        self.assertNotIn(tuple(task["probe"]["x"]), memory_xs)
        prompt = render_user(task)
        self.assertIn("Resolved decision:", prompt)
        self.assertNotIn("confidence", prompt.lower())
        self.assertNotIn("prediction", prompt.lower())

    def test_macro_call_accounting_is_frozen(self):
        counts = macro_expected_calls()
        self.assertEqual(counts["t0"], 2048)
        self.assertEqual(counts["online"], 36864)
        self.assertEqual(counts["post_checkpoints"], 147456)
        self.assertEqual(counts["total"], 186368)

    def test_serial_and_concurrent_mock_protocol_are_identical(self):
        import asyncio
        serial = asyncio.run(run_mock_protocol(1))
        concurrent = asyncio.run(run_mock_protocol(32))
        self.assertEqual(serial["t0"], concurrent["t0"])
        self.assertEqual(serial["trajectories"], concurrent["trajectories"])
        self.assertGreater(concurrent["max_active"], 1)
        self.assertLessEqual(concurrent["max_active"], 32)

    def test_mock_trajectory_isolation_and_checkpoint_immutability(self):
        import asyncio
        result = asyncio.run(run_mock_protocol(32))
        for trajectory in result["trajectories"]:
            self.assertEqual(trajectory["final_memory"], trajectory["events"][-1]["memory"])
            self.assertEqual(trajectory["final_posterior"], trajectory["events"][-1]["posterior"])
            self.assertEqual(len([e for e in trajectory["events"] if "checkpoint" in e]), 2)

    def test_concurrent_jsonl_logging_has_no_truncated_records(self):
        import asyncio
        import json
        import tempfile
        from pathlib import Path
        from emergent_specialization.theory_v1.macro_runner import append_jsonl

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            async def write(i):
                append_jsonl(path, {"logical_call_id": f"mock-{i}", "value": i})
            async def run_writes():
                await asyncio.gather(*[write(i) for i in range(400)])
            asyncio.run(run_writes())
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(rows), 400)
            self.assertEqual(len({row["logical_call_id"] for row in rows}), 400)


if __name__ == "__main__":
    unittest.main()

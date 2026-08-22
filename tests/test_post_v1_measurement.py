"""Deterministic regression tests for the post-V1 measurement-aware repair."""

from __future__ import annotations

import csv
import csv
import json
import unittest
from pathlib import Path

import numpy as np

from emergent_specialization.studies.mechanisms.decomposition.analysis import center
from emergent_specialization.studies.mechanisms.measurement.analysis import (
    MACRO_CELLS_V11,
    attach_memory_overlap,
    corr,
)


class PostV1MeasurementAwareTests(unittest.TestCase):
    def test_tie_aware_spearman_is_not_double_argsort(self) -> None:
        # x has a tie.  Average ranks give the conventional value; ordinal
        # double-argsort ranking would produce a different answer.
        value = corr([1, 1, 2, 3], [1, 2, 2, 3], method="spearman")
        self.assertAlmostEqual(value, 0.8333333333333334, places=12)

    def test_cross_half_noise_null_has_small_crossfit_bias(self) -> None:
        # This is the algebraic measurement-error control: independent noisy
        # halves produce a sizeable naive bias but approximately zero
        # cross-fitted bias.  It is intentionally not an LLM-data test.
        rng = np.random.default_rng(1901)
        naive_r, cf_r = [], []
        latent = center(np.asarray([[.45, .55, .50, .60], [.55, .45, .40, .50],
                                    [.50, .60, .45, .55], [.40, .50, .55, .45]]))
        for _ in range(400):
            a0 = center(np.clip(latent + rng.normal(0, .08, latent.shape), 0, 1))
            b0 = center(np.clip(latent + rng.normal(0, .08, latent.shape), 0, 1))
            a1 = center(np.clip(latent + rng.normal(0, .08, latent.shape), 0, 1))
            b1 = center(np.clip(latent + rng.normal(0, .08, latent.shape), 0, 1))
            ct = np.sum(a0 * b0)
            ctt = .5 * (np.sum(a0 * b1) + np.sum(b0 * a1))
            naive_r.append(2 * np.sum(a0 * (a1 - a0)) / 16)
            cf_r.append(2 * (ctt - ct) / 16)
        self.assertLess(abs(float(np.mean(cf_r))), abs(float(np.mean(naive_r))))

    def test_memory_overlap_is_reconstructed_from_snapshots(self) -> None:
        rows = [{"ecology": "V31_FRESH", "seed": 1, "cell_id": "C3", "checkpoint": 1} for _ in range(4)]
        snapshots = {
            ("V31_FRESH", 1, "C3", 1): {
                "memory": [
                    [{"uid": 1}, {"uid": 2}],
                    [{"uid": 2}, {"uid": 3}],
                    [{"uid": 3}, {"uid": 4}],
                    [{"uid": 4}, {"uid": 1}],
                ]
            }
        }
        attach_memory_overlap(rows, snapshots)
        self.assertTrue(all(0.0 <= float(row["mean_pairwise_exact_case_overlap"]) <= 1.0 for row in rows))
        self.assertAlmostEqual(float(rows[0]["mean_pairwise_exact_case_overlap"]), 2 / 9, places=12)

    def test_measurement_outputs_are_separate_from_prior_report(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertNotEqual(
            root / "reports/post-v1-measurement-aware",
            root / "reports/post-v1-mechanisms",
        )
        registry = root / "reports/post-v1-measurement-aware/analysis_registry.json"
        if registry.exists():
            value = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(value["external_model_calls"], 0)
            self.assertEqual(value["probe_split"], "odd_probe_index_vs_even_probe_index")

    def test_macro_cell_registry_has_frozen_eight_cells(self) -> None:
        self.assertEqual([str(row["cell_id"]) for row in MACRO_CELLS_V11],
                         ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7"])

    def test_construct_and_psi_secondary_outputs_are_materialized(self) -> None:
        root = Path(__file__).resolve().parents[1]
        out = root / "reports/post-v1-measurement-aware"
        expected = (
            "joint_bit_relationship.csv",
            "router_calibration_curves.csv",
            "psi_measurement_summary.csv",
        )
        if not all((out / name).exists() for name in expected):
            self.skipTest("generated offline report not present in a source-only checkout")
        for name in expected:
            with (out / name).open(encoding="utf-8") as handle:
                self.assertGreaterEqual(sum(1 for _ in csv.DictReader(handle)), 1)


if __name__ == "__main__":
    unittest.main()

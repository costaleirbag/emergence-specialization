"""Small deterministic tests for the post-V1 offline mechanism diagnostics."""

from __future__ import annotations

import json
import unittest

import numpy as np

from emergent_specialization.studies.mechanisms.decomposition.analysis import (
    center,
    cosine,
    memory_features,
    pmat,
    selected_from_p,
)
from emergent_specialization.studies.theory.v1.dynamics import psi_spec


class PostV1MechanismTests(unittest.TestCase):
    def test_double_center_removes_row_and_column_only_effects(self) -> None:
        base = np.full((4, 4), 0.5)
        row_only = base + np.arange(4, dtype=float)[:, None]
        col_only = base + np.arange(4, dtype=float)[None, :]
        self.assertTrue(np.allclose(center(base), 0.0))
        self.assertTrue(np.allclose(center(row_only), 0.0))
        self.assertTrue(np.allclose(center(col_only), 0.0))

    def test_delta_psi_identity(self) -> None:
        a0 = np.asarray([[.1, .2, .3, .4], [.4, .3, .2, .1], [.2, .1, .4, .3], [.3, .4, .1, .2]])
        a1 = np.asarray([[.2, .3, .2, .3], [.3, .2, .3, .2], [.1, .2, .5, .2], [.4, .3, .0, .3]])
        z0, dz = center(a0), center(a1 - a0)
        reinforcement = 2 * float(np.sum(z0 * dz)) / a0.size
        innovation = float(np.sum(dz * dz)) / a0.size
        self.assertAlmostEqual(psi_spec(a1) - psi_spec(a0), reinforcement + innovation, places=12)

    def test_router_policy_and_inverse_selection(self) -> None:
        probabilities = pmat([0.1, 0.2, 0.3, 0.4], beta=4.0, epsilon=0.1)
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=12)
        self.assertEqual(selected_from_p(probabilities, 0.0), 0)
        self.assertEqual(selected_from_p(probabilities, 0.999999999), 3)

    def test_memory_ladder_features_are_deterministic_and_padded(self) -> None:
        memory = [
            {"niche": 0},
            {"niche": 1},
            {"niche": 1},
        ]
        self.assertEqual(memory_features(memory, "M0").tolist(), [1.0, 2.0, 0.0, 0.0])
        self.assertEqual(memory_features(memory, "M2").shape, (32,))
        self.assertEqual(memory_features(memory, "M3").shape, (144,))
        self.assertTrue(np.array_equal(memory_features(memory, "M2"), memory_features(memory, "M2")))

    def test_cosine_is_explicitly_undefined_for_zero_vectors(self) -> None:
        self.assertIsNone(cosine(np.zeros((2, 2)), np.ones((2, 2))))
        self.assertAlmostEqual(cosine(np.eye(2), np.eye(2)), 1.0)

    def test_raw_hash_manifest_is_explicit_and_no_external_calls(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        manifest = root / "reports/post-v1-mechanisms/raw_hash_manifest.json"
        if not manifest.exists():
            self.skipTest("generated offline report not present in a source-only checkout")
        value = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(value["external_model_calls"], 0)
        self.assertTrue(value["before_after_equal"])
        self.assertEqual(len(value["files"]), 5)


if __name__ == "__main__":
    unittest.main()

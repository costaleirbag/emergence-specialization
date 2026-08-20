from __future__ import annotations

import unittest

import numpy as np

from emergent_specialization.semantic_ecology import GEOMETRY_ECOLOGIES
from emergent_specialization.transfer_geometry import SEEDS, build_tasks, expected_calls
from emergent_specialization.transfer_analysis import _alignment, _stable_seed
from emergent_specialization.transfer_operator import (
    analytical_jacobian,
    block_matrix,
    block_modes,
    centered_transfer,
    finite_difference_jacobian,
    geometry_metrics,
    eigenvector_condition,
    numerical_abscissa,
    projection,
    rayleigh,
    transient_amplification,
    toy_rhs,
)


class TransferOperatorTests(unittest.TestCase):
    def test_offline_alignment_and_bootstrap_seed_are_deterministic(self):
        identity = np.eye(4)
        first = _alignment("DIAGONAL", "natural", identity)
        second = _alignment("DIAGONAL", "natural", identity)
        self.assertEqual(first, second)
        self.assertEqual(_stable_seed("geometry", "policy"), _stable_seed("geometry", "policy"))
    def test_projection_properties(self):
        p = projection(4)
        self.assertTrue(np.allclose(p @ p, p))
        self.assertTrue(np.allclose(p @ np.ones(4), 0.0))

    def test_flat_limit_has_no_centered_drive(self):
        self.assertTrue(np.allclose(centered_transfer(np.full((4, 4), 2.0)), 0.0))

    def test_diagonal_limit_has_three_equal_contrast_modes(self):
        t = centered_transfer(np.eye(4) * 3.0)
        values = np.linalg.eigvals(t)
        self.assertTrue(np.allclose(sorted(values), [0.0, 0.75, 0.75, 0.75]))

    def test_block_modes_and_rayleigh_quotients(self):
        matrix = block_matrix(5.0, 2.0, 0.5)
        modes = block_modes(5.0, 2.0, 0.5)
        t = centered_transfer(matrix)
        self.assertAlmostEqual(rayleigh(t, [1, 1, -1, -1]), modes["block_T"])
        self.assertAlmostEqual(rayleigh(t, [1, -1, 0, 0]), modes["within_T"])

    def test_finite_difference_jacobian_matches_analytic_at_exchangeability(self):
        matrix = np.array([[1.0, 0.2, 0.0, 0.1], [0.1, 1.0, 0.3, 0.0], [0.0, 0.2, 1.0, 0.4], [0.3, 0.0, 0.1, 1.0]])
        state = np.zeros((4, 4))
        analytic = analytical_jacobian(matrix, N=4, beta=2.0, eta=0.7, gamma=0.1)
        numeric = finite_difference_jacobian(state, matrix, beta=2.0, eta=0.7, gamma=0.1)
        self.assertTrue(np.allclose(analytic, numeric, atol=1e-7))

    def test_nonsymmetric_susceptibility_uses_real_eigenvalue(self):
        matrix = np.array([[0, 2], [-3, 0]], dtype=float)
        result = geometry_metrics(matrix)
        expected = float(np.max(np.real(np.linalg.eigvals(centered_transfer(matrix)))))
        self.assertAlmostEqual(result["chi"], expected)

    def test_nonnormal_diagnostics_are_explicit_analysis_objects(self):
        matrix = np.array([[0.0, 3.0], [0.0, -1.0]])
        self.assertGreater(numerical_abscissa(matrix), 0.0)
        curve = transient_amplification(matrix, (0.0, 0.5, 1.0))
        self.assertEqual([row["t"] for row in curve], [0.0, 0.5, 1.0])
        self.assertAlmostEqual(curve[0]["amplification"], 1.0)
        self.assertIsNotNone(eigenvector_condition(matrix))


class GeometryGeneratorTests(unittest.TestCase):
    def test_designed_overlap_matrices_are_exact(self):
        for geometry, ecology in GEOMETRY_ECOLOGIES.items():
            env = ecology.generate_environment(SEEDS[0])
            g = env.metadata["designed_overlap"]
            self.assertTrue(all(abs(g[i][i] - 1.0) < 1e-12 for i in range(4)))
            if geometry == "GLOBAL":
                self.assertTrue(all(abs(g[i][j] - 2/3) < 1e-12 for i in range(4) for j in range(4) if i != j))
            elif geometry == "BLOCK":
                self.assertTrue(all(abs(g[i][j] - (2/3 if (i//2 == j//2) else 0.0)) < 1e-12 for i in range(4) for j in range(4) if i != j))
            else:
                self.assertTrue(all(abs(g[i][j]) < 1e-12 for i in range(4) for j in range(4) if i != j))

    def test_full_manifest_count_and_nested_natural_stream(self):
        self.assertEqual(expected_calls()["total"], 11520)
        tasks = build_tasks("BLOCK", SEEDS[:1])
        self.assertEqual(len(tasks), 768)
        h4 = {(t["target"], t["source"], t["exposure_policy"], t["replicate"], t["case"]["case_id"]): t for t in tasks if t["h"] == 4}
        for key, task in h4.items():
            if task["exposure_policy"] in {"natural", "teaching"}:
                matching = [t for t in tasks if t["h"] == 8 and t["seed"] == task["seed"] and t["target"] == task["target"] and t["source"] == task["source"] and t["exposure_policy"] == task["exposure_policy"] and t["replicate"] == task["replicate"] and t["case"]["case_id"] == task["case"]["case_id"]]
                self.assertEqual(len(matching), 1)
                self.assertEqual(task["memory"], matching[0]["memory"][:4])

    def test_foreign_control_preserves_family_and_changes_seed(self):
        tasks = build_tasks("GLOBAL", SEEDS[:2])
        foreign = [t for t in tasks if t["exposure_policy"] == "foreign_theta"]
        self.assertTrue(foreign)
        self.assertTrue(all(t["memory_environment_seed"] != t["seed"] for t in foreign))


if __name__ == "__main__":
    unittest.main()

import unittest

import numpy as np

from emergent_specialization.theory_v1.dynamics import centered_projector
from emergent_specialization.theory_v1 import forensic_repair
from emergent_specialization.theory_v1.forensic_repair import (
    QUARANTINE_ID,
    assert_scientific_run_allowed,
    centered_spectrum,
    inventory,
    reconstruct_checkpoint_records,
)
from emergent_specialization.theory_v1.prediction import predictions_for_k


class TheoryV1ForensicTests(unittest.TestCase):
    def test_repaired_prediction_rows_have_cell_matching_k(self):
        for k in (4, 8, 12):
            rows = predictions_for_k(np.eye(4), k)
            self.assertEqual(len(rows), 8 if k == 8 else 5)
            self.assertTrue(all(int(row["k"]) == k for row in rows))

    def test_centered_spectrum_has_no_uniform_mode(self):
        matrix = np.diag([3.0, 1.0, 1.0, 1.0])
        summary = centered_spectrum(matrix, 8, 0.0, 0.1, 0.0)
        self.assertEqual(len(summary["centered_eigenvalues_real"]), 3)
        self.assertAlmostEqual(summary["full_spectral_radius"], 0.96875)
        self.assertEqual(len(summary["dominant_mode"]), 4)
        self.assertAlmostEqual(float(np.sum(summary["dominant_mode"])), 0.0, places=10)

    def test_live_inventory_reconstructs_exactly_31_auxiliary_rows(self):
        required = (
            forensic_repair.MICRO_MANIFEST,
            forensic_repair.MACRO_MANIFEST,
            forensic_repair.MICRO_RAW,
            forensic_repair.MACRO_RAW,
            forensic_repair.MACRO_CHECKPOINTS_RAW,
        )
        if not all(path.exists() for path in required):
            self.skipTest("requires local Theory V1 raw run manifests and journals")
        inv = inventory()
        self.assertEqual(inv["macro_terminal_completions"], 186368)
        self.assertEqual(inv["checkpoint_missing_auxiliary"], 31)
        self.assertFalse(inv["quarantine_used_scientifically"])

    def test_projector_removes_constant_components(self):
        p = centered_projector(4)
        self.assertTrue(np.allclose(p @ np.ones(4), 0.0))

    def test_quarantined_run_is_hard_rejected(self):
        with self.assertRaises(ValueError):
            assert_scientific_run_allowed(QUARANTINE_ID)
        assert_scientific_run_allowed("theory-v1-macro-confirmatory-restarted-20260812")



if __name__ == "__main__":
    unittest.main()

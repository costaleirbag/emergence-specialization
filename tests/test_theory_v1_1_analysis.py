from __future__ import annotations

import unittest

from emergent_specialization.theory_v1_1_analysis import (
    _rank_corr,
    expected_checkpoint_ids,
    expected_t0_ids,
)


class TheoryV11AnalysisTests(unittest.TestCase):
    def test_expected_probe_cardinality(self):
        self.assertEqual(len(expected_t0_ids()), 2 * 6 * 4 * 4 * 8)
        self.assertEqual(len(expected_checkpoint_ids()), 2 * 6 * 8 * 4 * 4 * 4 * 8)

    def test_spearman_is_tie_aware_and_directional(self):
        self.assertAlmostEqual(_rank_corr([1, 1, 2], [2, 2, 3]), 1.0)
        self.assertAlmostEqual(_rank_corr([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertIsNone(_rank_corr([1, 1], [1, 2]))


if __name__ == "__main__":
    unittest.main()

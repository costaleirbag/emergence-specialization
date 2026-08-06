from __future__ import annotations

import math
import unittest

from emergent_specialization.metrics.hse import hierarchic_social_entropy


class HSETests(unittest.TestCase):
    def test_identical_behavioral_vectors_have_zero_hse(self) -> None:
        result = hierarchic_social_entropy([[1, 0, 1], [1, 0, 1], [1, 0, 1]])
        self.assertAlmostEqual(result["hse"], 0.0)
        self.assertAlmostEqual(result["normalized_hse"], 0.0)

    def test_mutually_orthogonal_toy_vectors_have_maximal_hse(self) -> None:
        result = hierarchic_social_entropy([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertAlmostEqual(result["hse"], math.log2(3))
        self.assertAlmostEqual(result["normalized_hse"], 1.0)

    def test_zero_vector_handling_is_explicit(self) -> None:
        result = hierarchic_social_entropy([[0, 0], [0, 0], [1, 0]])
        self.assertGreater(result["hse"], 0.0)
        self.assertEqual(result["distance_matrix"][0][1], 0.0)
        self.assertEqual(result["distance_matrix"][0][2], 1.0)

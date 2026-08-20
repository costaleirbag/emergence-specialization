from __future__ import annotations

import unittest

from emergent_specialization.hse_robustness import behavioral_distance, normalized_hierarchical_diversity


class HSERobustnessTests(unittest.TestCase):
    def test_distances_have_explicit_zero_and_binary_semantics(self) -> None:
        self.assertEqual(behavioral_distance([0, 0], [0, 0], "cosine"), 0.0)
        self.assertEqual(behavioral_distance([0, 0], [0, 0], "jaccard"), 0.0)
        self.assertEqual(behavioral_distance([1, 0], [0, 1], "hamming"), 1.0)

    def test_identical_vectors_have_zero_diversity_for_every_linkage(self) -> None:
        for linkage in ("single", "complete", "average"):
            self.assertEqual(normalized_hierarchical_diversity([[1, 0], [1, 0], [1, 0]], "cosine", linkage), 0.0)

    def test_orthogonal_vectors_have_maximal_diversity(self) -> None:
        matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        for linkage in ("single", "complete", "average"):
            self.assertAlmostEqual(normalized_hierarchical_diversity(matrix, "cosine", linkage), 1.0)

    def test_complete_and_average_are_deterministic(self) -> None:
        matrix = [[1, 1, 0, 0], [1, 0, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1]]
        for distance in ("cosine", "hamming", "jaccard"):
            for linkage in ("single", "complete", "average"):
                self.assertEqual(normalized_hierarchical_diversity(matrix, distance, linkage), normalized_hierarchical_diversity(matrix, distance, linkage))


if __name__ == "__main__":
    unittest.main()

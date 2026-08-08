from __future__ import annotations

import unittest

from emergent_specialization.metrics.complementarity import complementarity_metrics
from emergent_specialization.metrics.differentiation import (
    competence_differentiation_phi,
    competence_spectral_differentiation,
    division_of_labor_matching,
    routing_alignment,
)
from emergent_specialization.metrics.information import (
    mutual_information,
    normalized_mutual_information,
    normalized_utilization_entropy,
)


class MetricTests(unittest.TestCase):
    def test_oracle_gain_detects_complementarity(self) -> None:
        result = complementarity_metrics([[1, 0, 0, 1], [0, 1, 1, 0]])
        self.assertEqual(result["best_individual_accuracy"], 0.5)
        self.assertEqual(result["oracle_society_accuracy"], 1.0)
        self.assertEqual(result["oracle_gain"], 0.5)

    def test_task_agent_mutual_information_is_normalized(self) -> None:
        worlds = ["ALPHA", "ALPHA", "BETA", "BETA"]
        agents = ["agent_0", "agent_0", "agent_1", "agent_1"]
        self.assertAlmostEqual(mutual_information(worlds, agents), 1.0)
        self.assertAlmostEqual(normalized_mutual_information(worlds, agents), 1.0)

    def test_utilization_entropy_detects_routing_collapse(self) -> None:
        self.assertEqual(normalized_utilization_entropy(["agent_0"] * 10, 4), 0.0)

    def test_phi_is_zero_for_identical_competence_rows(self) -> None:
        self.assertEqual(competence_differentiation_phi([[0.5, 0.25], [0.5, 0.25]]), 0.0)

    def test_phi_level_and_developmental_contrasts_are_distinct_and_label_invariant(self) -> None:
        private_0 = [[0.0, 0.0], [1.0, 1.0]]
        shared_0 = [[0.0, 0.0], [0.0, 0.0]]
        private_t = [[0.0, 0.0], [0.0, 0.0]]
        shared_t = [[0.0, 0.0], [1.0, 1.0]]
        phi_private_0 = competence_differentiation_phi(private_0)
        phi_shared_0 = competence_differentiation_phi(shared_0)
        phi_private_t = competence_differentiation_phi(private_t)
        phi_shared_t = competence_differentiation_phi(shared_t)
        level = phi_private_t - phi_shared_t
        developmental = (phi_private_t - phi_private_0) - (phi_shared_t - phi_shared_0)
        self.assertNotEqual(level, developmental)
        self.assertAlmostEqual(competence_differentiation_phi(list(reversed(private_t))), phi_private_t)
        self.assertEqual(competence_differentiation_phi([[0.0, 0.0], [0.0, 0.0]]), 0.0)

    def test_phi_is_label_permutation_invariant_and_positive_for_differentiation(self) -> None:
        matrix = [[1.0, 0.0], [0.0, 1.0]]
        self.assertGreater(competence_differentiation_phi(matrix), 0.0)
        self.assertEqual(competence_differentiation_phi(matrix), competence_differentiation_phi(list(reversed(matrix))))

    def test_routing_alignment_has_random_and_oracle_endpoints(self) -> None:
        competence = {"agent_0": {"ALPHA": 1.0, "BETA": 0.0}, "agent_1": {"ALPHA": 0.0, "BETA": 1.0}}
        oracle = {"ALPHA": {"agent_0": 1}, "BETA": {"agent_1": 1}}
        random_like = {"ALPHA": {"agent_0": 1, "agent_1": 1}, "BETA": {"agent_0": 1, "agent_1": 1}}
        self.assertAlmostEqual(routing_alignment(oracle, competence)["eta_route"], 1.0)
        self.assertAlmostEqual(routing_alignment(random_like, competence)["eta_route"], 0.0)

    def test_routing_alignment_can_be_negative(self) -> None:
        competence = {"agent_0": {"ALPHA": 1.0, "BETA": 0.0}, "agent_1": {"ALPHA": 0.0, "BETA": 1.0}}
        bad = {"ALPHA": {"agent_1": 1}, "BETA": {"agent_0": 1}}
        self.assertLess(routing_alignment(bad, competence)["eta_route"], 0.0)

    def test_matching_reports_useful_one_to_one_potential(self) -> None:
        result = division_of_labor_matching(
            {"agent_0": {"ALPHA": 1.0, "BETA": 0.0}, "agent_1": {"ALPHA": 0.0, "BETA": 1.0}}
        )
        self.assertAlmostEqual(result["u_match"], 1.0)
        self.assertAlmostEqual(result["u_single"], 0.5)
        self.assertAlmostEqual(result["delta_match"], 0.5)

    def test_spectral_differentiation_has_explicit_zero_convention(self) -> None:
        result = competence_spectral_differentiation([[0.5, 0.25], [0.5, 0.25]])
        self.assertEqual(result["participation_ratio"], 0.0)

    def test_spectral_rank_one_has_effective_dimension_one(self) -> None:
        result = competence_spectral_differentiation([[1.0, 1.0], [0.0, 0.0]])
        self.assertAlmostEqual(result["participation_ratio"], 1.0, places=6)

    def test_spectral_dimension_is_label_permutation_invariant(self) -> None:
        matrix = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 0.0]]
        forward = competence_spectral_differentiation(matrix)
        reverse = competence_spectral_differentiation(list(reversed(matrix)))
        self.assertAlmostEqual(forward["participation_ratio"], reverse["participation_ratio"], places=6)
        self.assertGreater(forward["participation_ratio"], 1.0)

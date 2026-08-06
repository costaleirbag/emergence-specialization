from __future__ import annotations

import unittest

from emergent_specialization.metrics.complementarity import complementarity_metrics
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

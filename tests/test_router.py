from __future__ import annotations

import random
import unittest

from emergent_specialization.models import AgentResponse
from emergent_specialization.router import ConfidenceRouter


class RouterTests(unittest.TestCase):
    def test_ties_are_reproducible_from_rng(self) -> None:
        responses = [AgentResponse("agent_0", 1, 0.5), AgentResponse("agent_1", 2, 0.5)]
        router = ConfidenceRouter()
        first = router.select(responses, random.Random(17))
        second = router.select(responses, random.Random(17))
        self.assertEqual(first, second)
        self.assertEqual(first.tied_agent_ids, ("agent_0", "agent_1"))

    def test_higher_confidence_wins_without_exploration(self) -> None:
        responses = [AgentResponse("agent_0", 1, 0.2), AgentResponse("agent_1", 2, 0.8)]
        decision = ConfidenceRouter().select(responses, random.Random(1))
        self.assertEqual(decision.selected_agent_id, "agent_1")

    def test_probe_routing_is_deterministic(self) -> None:
        responses = [AgentResponse("agent_2", 1, 0.8), AgentResponse("agent_1", 2, 0.8)]
        self.assertEqual(ConfidenceRouter.deterministic_probe_choice(responses), "agent_1")

from __future__ import annotations

import random
import unittest

from emergent_specialization.models import AgentResponse
from emergent_specialization.router import ConfidenceRouter, RandomRouter


class RouterTests(unittest.TestCase):
    def test_ties_are_reproducible_from_rng(self) -> None:
        responses = [AgentResponse("agent_0", 1, 0.5), AgentResponse("agent_1", 2, 0.5)]
        router = ConfidenceRouter()
        first = router.select(responses, random.Random(17))
        second = router.select(responses, random.Random(17))
        self.assertEqual(first, second)
        self.assertEqual(first.tied_agent_ids, ("agent_0", "agent_1"))

    def test_tie_selection_is_independent_of_response_iteration_order(self) -> None:
        responses = [AgentResponse(f"agent_{index}", 1, 0.5) for index in range(4)]
        router = ConfidenceRouter()
        forward = router.select(responses, random.Random(19))
        reverse = router.select(list(reversed(responses)), random.Random(19))
        self.assertEqual(forward, reverse)

    def test_higher_confidence_wins_without_exploration(self) -> None:
        responses = [AgentResponse("agent_0", 1, 0.2), AgentResponse("agent_1", 2, 0.8)]
        decision = ConfidenceRouter().select(responses, random.Random(1))
        self.assertEqual(decision.selected_agent_id, "agent_1")

    def test_probe_routing_is_deterministic(self) -> None:
        responses = [AgentResponse("agent_2", 1, 0.8), AgentResponse("agent_1", 2, 0.8)]
        self.assertEqual(ConfidenceRouter.deterministic_probe_choice(responses), "agent_1")

    def test_random_router_ignores_confidence_and_is_order_invariant(self) -> None:
        responses = [
            AgentResponse("agent_0", 1, 0.01),
            AgentResponse("agent_1", 2, 0.99),
            AgentResponse("agent_2", 3, 0.50),
        ]
        router = RandomRouter()
        forward = router.select(responses, random.Random(23))
        reverse = router.select(list(reversed(responses)), random.Random(23))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward.selection_mode, "random")
        self.assertEqual(forward.tied_agent_ids, ("agent_0", "agent_1", "agent_2"))

    def test_random_router_probe_choice_uses_rng_not_confidence(self) -> None:
        responses = [AgentResponse("agent_0", 1, 0.01), AgentResponse("agent_1", 2, 0.99)]
        self.assertEqual(RandomRouter().probe_choice(responses, random.Random(4)), "agent_0")

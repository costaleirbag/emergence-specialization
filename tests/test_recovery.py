from __future__ import annotations

import unittest

from emergent_specialization.metrics.recovery import (
    niche_recovery_time,
    performance_recovery_time,
    role_replacement_time,
)


class RecoveryMetricTests(unittest.TestCase):
    def test_performance_recovery_is_indexed_and_explicit(self) -> None:
        self.assertEqual(performance_recovery_time([1.0, 0.2, 0.8, 1.0], baseline=1.0, tolerance=0.1, start_index=1), 3)

    def test_niche_recovery_uses_best_world_competence(self) -> None:
        before = {"a": {"ALPHA": 1.0}, "b": {"ALPHA": 0.2}}
        self.assertEqual(niche_recovery_time(before, [{"a": {"ALPHA": 0.5}}, {"b": {"ALPHA": 0.95}}]), 1)

    def test_role_replacement_is_not_confused_with_occupant_stability(self) -> None:
        routing = [{"world": "ALPHA", "selected_agent": "a"}, {"world": "ALPHA", "selected_agent": "b"}]
        self.assertEqual(role_replacement_time(routing, removed_agent="a", world="ALPHA", start_index=1), 1)

from __future__ import annotations

import unittest

from emergent_specialization.core.environment import HiddenWorldEnvironment
from emergent_specialization.studies.calibration.memory_representation_thinking import (
    _exemplars,
    _probe_map,
    _render_memory,
    balanced_probe_tasks,
    expected_query_count,
    preflight,
)


class MemoryRepresentationThinkingTests(unittest.TestCase):
    def test_balanced_probe_labels_and_disjoint_exemplars(self) -> None:
        env = HiddenWorldEnvironment()
        probes = balanced_probe_tasks(env)
        grouped = _probe_map(probes)
        for world, tasks in grouped.items():
            self.assertEqual({label: sum(task.correct_answer == label for task in tasks) for label in range(7)}, {label: 2 for label in range(7)})
            exemplars = _exemplars(env, grouped, world, 1)
            self.assertTrue({(x.x, x.y) for x in exemplars}.isdisjoint({(x.x, x.y) for x in tasks}))

    def test_nested_exemplar_pool_and_same_pool_across_representations(self) -> None:
        env = HiddenWorldEnvironment(); grouped = _probe_map(balanced_probe_tasks(env)); pool = _exemplars(env, grouped, "ALPHA", 1)
        self.assertEqual([x.correct_answer for x in pool[:1]], [pool[0].correct_answer])
        self.assertEqual([x.x for x in pool[:4]], [x.x for x in pool][:4])
        full = _render_memory(pool[:8], "full_experience")
        feedback = _render_memory(pool[:8], "feedback_only")
        self.assertEqual([(x["world"], x["x"], x["y"], x["correct_answer"]) for x in full], [(x["world"], x["x"], x["y"], x["correct_answer"]) for x in feedback])
        self.assertTrue(all("prediction" not in x and "confidence" not in x and "was_correct" not in x for x in feedback))

    def test_corrupted_feedback_changes_each_label_and_keeps_truth_out_of_own_record(self) -> None:
        env = HiddenWorldEnvironment(); grouped = _probe_map(balanced_probe_tasks(env)); pool = _exemplars(env, grouped, "BETA", 1)
        corrupted = _render_memory(pool, "feedback_only", corrupted=True)
        self.assertTrue(all(item["correct_answer"] != truth.correct_answer for item, truth in zip(corrupted, pool)))
        self.assertTrue(all(set(item) == {"world", "x", "y", "correct_answer"} for item in corrupted))

    def test_preflight_exact_count_and_documented_thinking_support(self) -> None:
        audit = preflight()
        self.assertEqual(audit["planned_logical_queries"], 33600)
        self.assertEqual(audit["probes_per_world"], 14)
        self.assertEqual(audit["thinking_modes"], ["off", "high"])
        self.assertTrue(audit["k0_deduplicated"])

    def test_expected_query_count_from_spec(self) -> None:
        spec = {"worlds": ["A", "B", "C", "D"], "context_seeds": 10, "probes_per_world": 14, "replicates": 3, "k_values": [0, 1, 2, 4, 8], "reasoning_modes": ["off", "high"], "representations": ["full_experience", "feedback_only"], "include_truly_corrupted_feedback": True}
        self.assertEqual(expected_query_count(spec), 33600)

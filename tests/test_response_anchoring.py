from __future__ import annotations

import unittest

from emergent_specialization.response_anchoring import anchoring_metrics


class ResponseAnchoringTests(unittest.TestCase):
    def test_empty_memory_is_undefined(self) -> None:
        values = anchoring_metrics(2, [])
        self.assertIsNone(values["last_label"])
        self.assertIsNone(values["any_label"])

    def test_last_and_any_label_anchoring(self) -> None:
        memory = [
            {"prediction": 1, "correct_answer": 2},
            {"prediction": 4, "correct_answer": 5},
            {"prediction": 3, "correct_answer": 2},
        ]
        values = anchoring_metrics(2, memory)
        self.assertEqual(values["last_label"], 1.0)
        self.assertEqual(values["any_label"], 1.0)
        self.assertEqual(values["last_prediction"], 0.0)

    def test_modal_label_uses_deterministic_tie_breaking(self) -> None:
        values = anchoring_metrics(2, [{"prediction": 0, "correct_answer": 3}, {"prediction": 1, "correct_answer": 2}])
        self.assertEqual(values["modal_label"], 1.0)

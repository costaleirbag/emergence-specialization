from __future__ import annotations

import unittest

from emergent_specialization.costs import normalize_token_usage, summarize_usage


class CostAccountingTests(unittest.TestCase):
    def test_normalizes_common_provider_usage_shapes(self) -> None:
        usage = normalize_token_usage(
            {
                "prompt_tokens": 100,
                "completion_tokens": 25,
                "total_tokens": 125,
                "prompt_tokens_details": {"cached_tokens": 40},
                "completion_tokens_details": {"reasoning_tokens": 5},
            }
        )
        self.assertEqual(
            usage,
            {
                "input_tokens": 100,
                "cached_input_tokens": 40,
                "output_tokens": 25,
                "reasoning_tokens": 5,
                "total_tokens": 125,
            },
        )

    def test_cost_requires_complete_usage_and_explicit_rates(self) -> None:
        unavailable = summarize_usage([None], input_per_million_tokens=1, output_per_million_tokens=2)
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertIsNone(unavailable["estimated_cost"])

        estimated = summarize_usage(
            [{"input_tokens": 1000, "cached_input_tokens": 200, "output_tokens": 100}],
            input_per_million_tokens=1.0,
            cached_input_per_million_tokens=0.5,
            output_per_million_tokens=2.0,
        )
        self.assertEqual(estimated["status"], "estimated")
        self.assertEqual(estimated["total_tokens"], 1100)
        self.assertAlmostEqual(estimated["estimated_cost"], 0.0011)

    def test_partial_usage_is_not_presented_as_a_full_total(self) -> None:
        summary = summarize_usage([{"input_tokens": 10, "output_tokens": 2}, None])
        self.assertEqual(summary["status"], "partial_usage")
        self.assertEqual(summary["usage_coverage"], 0.5)
        self.assertIsNone(summary["total_tokens"])

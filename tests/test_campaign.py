from __future__ import annotations

import unittest

from emergent_specialization.campaign import (
    HARD_COST_CAP_USD,
    _apply_reuse,
    _forecast,
    build_campaign_plan,
    observed_baseline_cost_per_logical,
)


class CampaignPlanningTests(unittest.TestCase):
    def test_plan_has_registered_stage_sizes_and_call_counts(self) -> None:
        rows = build_campaign_plan()
        self.assertEqual(len(rows), 320)
        self.assertEqual(sum(row.stage == "A" for row in rows), 200)
        self.assertEqual(sum(row.stage == "B" for row in rows), 100)
        self.assertEqual(sum(row.stage == "C" for row in rows), 20)
        self.assertEqual({row.nominal_calls for row in rows if row.stage in {"A", "B"}}, {560})
        self.assertEqual({row.nominal_calls for row in rows if row.stage == "C"}, {2160})
        self.assertEqual({row.probe_set_hash for row in rows}, {"cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e"})

    def test_existing_seed_one_pair_is_reused_without_changing_plan(self) -> None:
        rows, reused = _apply_reuse(build_campaign_plan())
        self.assertEqual(len(reused), 2)
        self.assertEqual(sum(row.status == "reused" for row in rows), 2)
        self.assertEqual({row.seed for row in rows if row.status == "reused"}, {1})

    def test_forecast_is_hard_cap_aware(self) -> None:
        rows, _ = _apply_reuse(build_campaign_plan())
        per_logical = observed_baseline_cost_per_logical()
        forecast = _forecast(rows, per_logical)
        self.assertEqual(forecast["new_runs"], 318)
        self.assertGreater(float(forecast["projected_cost_usd"]), HARD_COST_CAP_USD)

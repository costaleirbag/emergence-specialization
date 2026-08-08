from __future__ import annotations

import unittest

from emergent_specialization.clean_campaign import (
    CONFIGS,
    PROTOCOL_VERSION,
    SEEDS,
    build_plan,
)


class CleanCampaignPlanningTests(unittest.TestCase):
    def test_clean_v2_is_exact_four_cell_ten_seed_plan(self) -> None:
        rows = build_plan()
        self.assertEqual(len(rows), 40)
        self.assertEqual({row.seed for row in rows}, set(SEEDS))
        self.assertEqual({(row.router, row.condition) for row in rows}, set(CONFIGS))
        self.assertEqual(sum(row.nominal_logical_completions for row in rows), 22400)
        self.assertEqual(sum(row.max_physical_attempts for row in rows), 28000)
        self.assertTrue(all(row.protocol_version == PROTOCOL_VERSION for row in rows))
        self.assertEqual({row.probe_set_hash for row in rows}, {
            "cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e"
        })

    def test_order_is_fixed_by_seed_then_cell(self) -> None:
        rows = build_plan()
        self.assertEqual(
            [(row.seed, row.router, row.condition) for row in rows[:4]],
            [(1, "confidence", "private"), (1, "confidence", "shared"),
             (1, "random", "private"), (1, "random", "shared")],
        )
        self.assertEqual(rows[-1].index, 39)


if __name__ == "__main__":
    unittest.main()

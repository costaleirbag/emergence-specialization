from __future__ import annotations

import unittest
from pathlib import Path

from emergent_specialization.config import AgentSettings, CostSettings, load_config


class ConfigTests(unittest.TestCase):
    def test_real_pilot_preserves_thinking_off_as_a_string(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "pilot_private.yaml")
        self.assertEqual(config.agent.thinking, "off")

    def test_boolean_yaml_coercion_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AgentSettings(thinking=False)  # type: ignore[arg-type]

    def test_cost_rates_are_optional_and_reject_negative_values(self) -> None:
        self.assertIsNone(CostSettings().input_per_million_tokens)
        with self.assertRaises(ValueError):
            CostSettings(output_per_million_tokens=-1)

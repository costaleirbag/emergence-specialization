from __future__ import annotations

import itertools
import inspect
import json
import unittest

from emergent_specialization import observable_learner_calibration as calibration
from emergent_specialization import observable_learner_calibration_v2 as calibration_v2
from emergent_specialization.theory_v1 import micro_runner
from emergent_specialization.theory_v1 import macro_runner
from emergent_specialization.theory_v1_1 import (
    CLEAN_OUTPUT_INSTRUCTION,
    ECOLOGIES,
    MACRO_CELLS_V11,
    STAGE_A_CONDITIONS,
    VALIDATION_SEEDS,
    build_stage_a_tasks,
    build_micro_tasks,
    render_user,
    _novel_seed_audit,
)
from emergent_specialization.theory_v1 import forensic_repair
from emergent_specialization import theory_v1_1_macro


class TheoryV11HarnessTests(unittest.TestCase):
    def test_static_instructions_contain_no_complete_binary_vector(self):
        instructions = (
            micro_runner.OUTPUT_INSTRUCTION,
            calibration.OUTPUT_INSTRUCTION,
            calibration_v2.OUTPUT_INSTRUCTION,
            CLEAN_OUTPUT_INSTRUCTION,
        )
        for instruction in instructions:
            compact = instruction.replace(" ", "")
            for bits in itertools.product((0, 1), repeat=3):
                self.assertNotIn(json.dumps(list(bits), separators=(",", ":")), compact)

    def test_stage_a_exact_count_and_fresh_seeds(self):
        tasks = build_stage_a_tasks()
        self.assertEqual(len(tasks), 1024)
        self.assertEqual({task["task"]["condition"] if "task" in task else task["condition"] for task in tasks}, set(STAGE_A_CONDITIONS))
        self.assertEqual({task["ecology"] for task in tasks}, set(ECOLOGIES))
        for ecology, seeds in VALIDATION_SEEDS.items():
            self.assertEqual({task["seed"] for task in tasks if task["ecology"] == ecology}, set(seeds))

    def test_same_h4_is_prefix_of_same_h8(self):
        tasks = build_stage_a_tasks()
        for ecology in ECOLOGIES:
            for seed in VALIDATION_SEEDS[ecology]:
                for target in range(4):
                    h4 = next(task for task in tasks if task["ecology"] == ecology and task["seed"] == seed and task["target"] == target and task["condition"] == "same_h4" and task["probe_index"] == 0)
                    h8 = next(task for task in tasks if task["ecology"] == ecology and task["seed"] == seed and task["target"] == target and task["condition"] == "same_h8" and task["probe_index"] == 0)
                    self.assertEqual(h4["memory"], h8["memory"][:4])

    def test_clean_render_has_neutral_static_schema(self):
        task = build_stage_a_tasks()[0]
        rendered = render_user(task["ecology"], task["probe"], task["memory"])
        self.assertIn('one key named "decisions"', rendered)
        self.assertNotIn('Return only JSON: {"decisions":[0,1,0]}', rendered)
        macro_rendered = macro_runner.render_user(task["ecology"], task["probe"], task["memory"])
        self.assertNotIn('Return only JSON: {"decisions":[0,1,0]}', macro_rendered)

    def test_fresh_seed_audit_uses_structured_declarations(self):
        audit = _novel_seed_audit()
        self.assertEqual(audit["collisions"], {})

    def test_exact_discriminating_macro_cells(self):
        self.assertEqual([cell["cell_id"] for cell in MACRO_CELLS_V11], [f"C{i}" for i in range(8)])
        self.assertEqual({(c["k"], c["beta"], c["epsilon"], c["q_share"]) for c in MACRO_CELLS_V11}, {
            (8, 0.0, .10, 0.0), (8, 4.0, .10, 0.0), (8, 8.0, .10, 0.0),
            (8, 12.0, .10, 0.0), (8, 20.0, .10, 0.0), (8, 16.0, .55, 0.0),
            (8, 12.0, .10, .5), (8, 12.0, .10, 1.0),
        })

    def test_micro_exact_count_and_fresh_seed_grid(self):
        tasks = build_micro_tasks()
        self.assertEqual(len(tasks), 19584)
        self.assertEqual({task["k"] for task in tasks}, {4, 8, 12})

    def test_historical_sensitivity_cannot_overwrite_primary_scorecard(self):
        source = inspect.getsource(forensic_repair.sensitivity_scorecards)
        self.assertIn("write_artifacts=False", source)

    def test_v11_macro_manifest_is_exact_target_grid(self):
        legacy_cells_before = macro_runner.macro_cells()
        manifest = theory_v1_1_macro.build_manifest()
        self.assertEqual(manifest["protocol"], "THEORY-V1.1")
        self.assertEqual(manifest["logical_calls"], 62976)
        self.assertEqual(len(manifest["cells"]), 8)
        self.assertEqual(manifest["social_seeds"], {k: list(v) for k, v in theory_v1_1_macro.SOCIAL_SEEDS_V11.items()})
        self.assertEqual(macro_runner.macro_cells(), legacy_cells_before)

    def test_v11_budget_amendment_is_macro_only(self):
        self.assertEqual(theory_v1_1_macro.MACRO_HARD_CAP_USD, 5.0)
        self.assertEqual(theory_v1_1_macro.HARD_CAP_USD, 4.0)


if __name__ == "__main__":
    unittest.main()

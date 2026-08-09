import json
import unittest

from emergent_specialization.observable_learner_calibration import (
    FAMILIES,
    GEOMETRIES,
    PROBE_COUNT,
    SEEDS,
    build_tasks,
    expected_calls,
    parse_decisions,
    render_user,
)


class ObservableLearnerCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = build_tasks()

    def test_frozen_call_count_and_breakdown(self):
        self.assertEqual(expected_calls(), {"baseline": 288, "transfer": 1152, "total": 1440})
        self.assertEqual(len(self.tasks), 1440)
        self.assertEqual(sum(t["condition"] == "baseline" for t in self.tasks), 288)
        self.assertEqual(sum(t["condition"] == "transfer" for t in self.tasks), 1152)

    def test_probe_balance_and_template_split(self):
        probes = {}
        for task in self.tasks:
            key = (task["geometry"], task["seed"], task["target"])
            probes.setdefault(key, {})[task["probe"]["case_id"]] = task["probe"]
        self.assertEqual(len(probes), 3 * 4 * 4)
        for values in probes.values():
            rows = list(values.values())
            self.assertEqual(len(rows), PROBE_COUNT)
            self.assertEqual(len({tuple(row["x"]) for row in rows}), PROBE_COUNT)
            self.assertTrue(all(row["template_id"] == 3 for row in rows))
            self.assertEqual([sum(row["y"][j] for row in rows) for j in range(3)], [3, 3, 3])

    def test_pairing_and_memory_are_condition_independent(self):
        baseline = {(t["geometry"], t["seed"], t["target"], t["probe"]["case_id"]): t for t in self.tasks if t["condition"] == "baseline"}
        transfer = [t for t in self.tasks if t["condition"] == "transfer"]
        self.assertEqual({t["geometry"] for t in transfer}, set(GEOMETRIES))
        self.assertEqual({t["seed"] for t in transfer}, set(SEEDS))
        self.assertTrue(all(len(t["memory"]) == 8 for t in transfer))
        self.assertTrue(all(t["source"] in FAMILIES and t["target"] in FAMILIES for t in transfer))
        self.assertTrue(all("family_id" not in render_user(t) and "theta" not in render_user(t).lower() for t in self.tasks))
        self.assertEqual(len(baseline), 288)

    def test_parser_accepts_only_three_binary_decisions(self):
        self.assertEqual(parse_decisions('{"decisions":[0,1,0]}'), ([0, 1, 0], None))
        self.assertEqual(parse_decisions('text {"decisions":[1,0,1]}'), ([1, 0, 1], None))
        self.assertEqual(parse_decisions('{"decisions":[0,1]}')[1], "out_of_domain")
        self.assertEqual(parse_decisions('{"answer":"APPROVE"}')[1], "parse_error")
        self.assertEqual(parse_decisions(None)[1], "empty_content")


if __name__ == "__main__":
    unittest.main()

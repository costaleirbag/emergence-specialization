import itertools
import re
import unittest

from emergent_specialization import observable_learner_calibration_v2 as v2


class ObservableLearnerCalibrationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not __import__("pathlib").Path(__file__).resolve().parents[1].joinpath(
            "reports/task-ecology/ecological-information-v31/observable_Lstar_natural.csv"
        ).exists():
            raise unittest.SkipTest("requires the local V3.1 observable baseline")
        cls.tasks = v2.build_tasks()

    def test_static_instructions_have_no_complete_vector(self):
        self.assertEqual(v2.static_triplet_leaks(), [])
        self.assertNotRegex(v2.OUTPUT_INSTRUCTION, re.compile(r"\[\s*[01]\s*,\s*[01]\s*,\s*[01]\s*\]"))

    def test_exact_count_and_probe_marginals(self):
        self.assertEqual(len(self.tasks), 1920)
        self.assertEqual(v2.expected_calls(), {"baseline": 384, "transfer": 1536, "total": 1920})
        for seed, xs in v2.probe_design().items():
            self.assertEqual(len(xs), 8)
            self.assertEqual(len(set(xs)), 8)
            for j in range(3):
                self.assertEqual([sum(x[j] == value for x in xs) for value in range(4)], [2, 2, 2, 2])

    def test_output_balance_follows_from_input_balance(self):
        for task in self.tasks:
            if task["condition"] != "baseline":
                continue
            # The eight symbolic probes are reused; any balanced hidden map
            # therefore yields four zeros and four ones per component.
            peers = [t for t in self.tasks if t["condition"] == "baseline" and t["geometry"] == task["geometry"] and t["seed"] == task["seed"] and t["target"] == task["target"]]
            for bit in range(3): self.assertEqual(sum(t["probe"]["y"][bit] for t in peers), 4)

    def test_history_overlap_and_geometry_pairing(self):
        for seed, xs in v2.probe_design().items():
            probe_set = set(xs)
            for source in v2.FAMILIES:
                streams = [tuple(tuple(r["x"]) for r in v2.history_for(g, seed, source)) for g in v2.GEOMETRIES]
                self.assertEqual(len(set(streams)), 1)
                self.assertTrue(probe_set.isdisjoint(streams[0]))

    def test_exact_bayes_gate_and_prompt_metadata(self):
        gate = v2._bayes_gate(self.tasks)
        self.assertTrue(gate["pass"])
        self.assertEqual(gate["independent_min"], 0.125)
        self.assertEqual(gate["independent_max"], 0.125)
        self.assertTrue(all("A_star_prompt" in task and "posterior" in task for task in self.tasks))


if __name__ == "__main__":
    unittest.main()

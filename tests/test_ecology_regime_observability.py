import inspect
import itertools
import unittest

from emergent_specialization import ecology_regime_observability as audit
from emergent_specialization import observable_learner_calibration_v2 as v2


class EcologyRegimeObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = __import__("json").loads((audit.V2_REPORT_ROOT / "manifest.json").read_text())
        cls.tasks = cls.manifest["tasks"]

    def test_full_oracle_reproduces_conditioned_v2(self):
        for task in self.tasks[::97]:
            full, _ = audit.oracle_posterior(task, "full")
            old = v2.exact_bayes(task)
            self.assertAlmostEqual(max(full), old["A_star_prompt"])
            self.assertAlmostEqual(full[list(itertools.product((0, 1), repeat=3)).index(tuple(task["probe"]["y"]))], old["p_true"])

    def test_hidden_oracle_marginalizes_regime_and_history_posterior_is_uniform(self):
        task = next(t for t in self.tasks if t["condition"] == "transfer")
        history = [audit.V3Case(item["family"], tuple(item["x"]), tuple(item["y"])) for item in task["memory"]]
        posterior = audit.history_regime_posterior(history, task["source"])
        for value in posterior.values():
            self.assertAlmostEqual(value, 1 / 3)
        _, weights = audit.oracle_posterior(task, "hidden")
        self.assertEqual(weights, posterior)

    def test_relation_weights_only_condition_on_pairwise_sharing(self):
        weights = audit._relation_weights("ACCESS", "RELEASE", "SAME_POLICY")
        self.assertAlmostEqual(weights["GLOBAL"], 0.5)
        self.assertAlmostEqual(weights["BLOCK"], 0.5)
        self.assertAlmostEqual(weights["DIAGONAL"], 0.0)
        weights = audit._relation_weights("ACCESS", "INCIDENT", "SAME_POLICY")
        self.assertAlmostEqual(weights["GLOBAL"], 1.0)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_probability_distributions_normalize(self):
        task = next(t for t in self.tasks if t["condition"] == "transfer")
        for mode in ("hidden", "relation", "full"):
            probs, _ = audit.oracle_posterior(task, mode)
            self.assertAlmostEqual(sum(probs), 1.0)

    def test_sharing_probabilities_are_exact_under_uniform_meta_prior(self):
        self.assertEqual([audit.relation_for(g, "ACCESS", "ACCESS") for g in audit.GEOMETRIES], ["SAME_POLICY"] * 3)
        self.assertEqual(sum(audit.relation_for(g, "ACCESS", "RELEASE") == "SAME_POLICY" for g in audit.GEOMETRIES), 2)
        self.assertEqual(sum(audit.relation_for(g, "ACCESS", "INCIDENT") == "SAME_POLICY" for g in audit.GEOMETRIES), 1)

    def test_prompt_aliasing_matches_frozen_counts(self):
        result = audit.prompt_aliasing(self.manifest)["summary"]
        self.assertEqual(result["cross_domain_triples"], 384)
        self.assertEqual(result["identical_all"], 96)
        self.assertEqual(result["different_truth_identical_all"], 91)

    def test_baseline_cancellation_algebra(self):
        # For balanced K×K matrices, each target baseline appears once on the
        # diagonal and K-1 times in the off-diagonal mean.
        k = 4
        baselines = [0.1, 0.2, 0.3, 0.4]
        diagonal = sum(baselines) / k
        offdiag = sum(baselines[j] for i in range(k) for j in range(k) if i != j) / (k * (k - 1))
        self.assertAlmostEqual(diagonal, offdiag)
        # The same target weights hold for the two two-edge BLOCK contrasts.
        within_targets = [1, 0, 3, 2]
        cross_targets = [2, 3, 0, 1]
        self.assertAlmostEqual(sum(baselines[j] for j in within_targets) / 4,
                               sum(baselines[j] for j in cross_targets) / 4)

    def test_pooled_baseline_changes_margins_but_not_q(self):
        # This is a frozen-data regression check for the prompt-identity audit.
        if not audit.REPORT_ROOT.joinpath("pooled_baseline_summary.json").exists():
            self.skipTest("requires the local pooled-baseline summary")
        summary = __import__("json").loads((audit.REPORT_ROOT / "pooled_baseline_summary.json").read_text())
        for original, pooled in zip(summary["original"], summary["pooled"]):
            self.assertAlmostEqual(original["Q"], pooled["Q"])
        self.assertAlmostEqual(summary["pooled"][0]["D"], 0.2868923611111111)

    def test_offline_module_has_no_external_inference_path(self):
        source = inspect.getsource(audit)
        self.assertNotIn("DeepSeekDirectBackend", source)
        self.assertNotIn("CredentialStore", source)
        self.assertNotIn("requests", source)


if __name__ == "__main__":
    unittest.main()

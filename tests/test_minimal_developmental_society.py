import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emergent_specialization.studies.society.minimal_developmental_society import (
    CHECKPOINTS,
    EVAL_COUNT,
    FAMILIES,
    MEMORY_K,
    NUM_AGENTS,
    REGIMES,
    SEEDS,
    UNKNOWN_USAGE_COST_USD,
    _one_completion,
    build_seed_spec,
    evaluation_support,
    expected_calls,
    matching_gain,
    parse_decisions,
    phi,
    psi_spec,
    route_probabilities,
    run_mock,
    sample_from_u,
)
from emergent_specialization.core.models import BackendResponse


class MinimalDevelopmentalSocietyTests(unittest.TestCase):
    def test_exact_call_budget(self):
        self.assertEqual(expected_calls(), {"t0": 2048, "online": 4096, "post_checkpoints": 40960, "total": 47104})

    def test_evaluation_support_is_balanced_and_held_out(self):
        for seed in SEEDS:
            spec = build_seed_spec(seed)
            xs = [tuple(x) for x in spec["evaluation_x"]]
            self.assertEqual(len(xs), EVAL_COUNT)
            for axis in range(3):
                self.assertEqual([sum(x[axis] == value for x in xs) for value in range(4)], [4, 4, 4, 4])
            self.assertFalse(set(xs) & {tuple(row["x"]) for row in spec["online_tasks"]})
            self.assertEqual({row["niche"] for row in spec["online_tasks"]}, set(FAMILIES))

    def test_task_stream_is_balanced_and_seed_deterministic(self):
        for seed in SEEDS:
            first, second = build_seed_spec(seed), build_seed_spec(seed)
            self.assertEqual(first["task_stream_hash"], second["task_stream_hash"])
            self.assertEqual(len(first["online_tasks"]), 128)
            for block in range(32):
                rows = first["online_tasks"][block * 4:(block + 1) * 4]
                self.assertEqual({row["niche"] for row in rows}, set(FAMILIES))

    def test_router_probabilities_and_common_random_number(self):
        for regime in REGIMES:
            probabilities = route_probabilities(regime, [0.125] * NUM_AGENTS)
            self.assertAlmostEqual(sum(probabilities), 1.0)
            self.assertTrue(all(value >= 0.10 / NUM_AGENTS for value in probabilities))
        # A label permutation with corresponding state permutation gives the
        # corresponding selected label under the same uniform draw.
        mu = [0.2, 0.4, 0.1, 0.3]
        p = route_probabilities("AP12", mu)
        permutation = [2, 0, 3, 1]
        pp = route_probabilities("AP12", [mu[i] for i in permutation])
        selected = sample_from_u(p, 0.37)
        selected_permuted = sample_from_u(pp, 0.37)
        self.assertEqual(permutation[selected_permuted], selected)

    def test_memory_and_metric_sanity(self):
        # A pure agent or niche main effect is removed by Psi_spec.
        self.assertAlmostEqual(psi_spec([[0.2, 0.2, 0.2, 0.2], [0.3, 0.3, 0.3, 0.3], [0.4, 0.4, 0.4, 0.4], [0.5, 0.5, 0.5, 0.5]]), 0.0)
        self.assertGreater(psi_spec([[1, 0, 0, 1], [0, 1, 1, 0], [0, 1, 1, 0], [1, 0, 0, 1]]), 0.0)
        self.assertAlmostEqual(phi([[1, 1], [1, 1]]), 0.0)
        self.assertGreater(matching_gain([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])[2], 0.0)

    def test_parser_terminal_semantics(self):
        self.assertEqual(parse_decisions('{"decisions":[1,0,1]}'), ([1, 0, 1], None))
        self.assertEqual(parse_decisions('{"decisions":[2,0,1]}')[1], "out_of_domain")
        self.assertEqual(parse_decisions("not json")[1], "parse_error")

    def test_offline_mock_harness(self):
        result = run_mock()
        self.assertEqual(result["status"], "MOCK ONLY — NOT SCIENTIFIC RESULT")

    def test_missing_usage_is_journaled_and_retried_once(self):
        class FakeBackend:
            def __init__(self):
                self.calls = 0

            async def complete(self, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    return BackendResponse(
                        raw_response='{"decisions":[1,0,1]}',
                        latency_s=0.01,
                        token_usage=None,
                        provider_metadata={"model": "deepseek-v4-flash"},
                    )
                return BackendResponse(
                    raw_response='{"decisions":[1,0,1]}',
                    latency_s=0.01,
                    token_usage={"prompt_tokens": 10, "completion_tokens": 5},
                    provider_metadata={"model": "deepseek-v4-flash"},
                )

        task = {"niche": FAMILIES[0], "x": [0, 1, 2], "y": [1, 0, 1], "template_id": 3}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            backend = FakeBackend(); attempts = {}
            with patch("emergent_specialization.studies.society.minimal_developmental_society._budget_update", return_value={}):
                result = asyncio.run(_one_completion(
                    backend, logical_id="logical", seed=SEEDS[0], regime="RP", phase="online",
                    checkpoint=1, agent=0, niche=FAMILIES[0], task=task, memory=[], existing={},
                    attempt_counts=attempts, events_path=path, semaphore=asyncio.Semaphore(1),
                ))
            events = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(backend.calls, 2)
        self.assertEqual([event["attempt"] for event in events], [0, 1])
        self.assertFalse(events[0]["terminal"])
        self.assertEqual(events[0]["error_category"], "usage_unavailable")
        self.assertEqual(events[0]["attempt_cost_usd"], UNKNOWN_USAGE_COST_USD)
        self.assertEqual(events[0]["cost_source"], "conservative_upper_bound_missing_usage")
        self.assertTrue(result["terminal"])
        self.assertEqual(attempts["logical"], 2)

    def test_resume_respects_previously_recorded_attempt(self):
        class FakeBackend:
            calls = 0

            async def complete(self, **_kwargs):
                self.calls += 1
                return BackendResponse(
                    raw_response='{"decisions":[1,0,1]}', latency_s=0.01,
                    token_usage={"prompt_tokens": 10, "completion_tokens": 5},
                    provider_metadata={"model": "deepseek-v4-flash"},
                )

        task = {"niche": FAMILIES[0], "x": [0, 1, 2], "y": [1, 0, 1], "template_id": 3}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"; backend = FakeBackend(); attempts = {"logical": 1}
            with patch("emergent_specialization.studies.society.minimal_developmental_society._budget_update", return_value={}):
                result = asyncio.run(_one_completion(
                    backend, logical_id="logical", seed=SEEDS[0], regime="RP", phase="online",
                    checkpoint=1, agent=0, niche=FAMILIES[0], task=task, memory=[], existing={},
                    attempt_counts=attempts, events_path=path, semaphore=asyncio.Semaphore(1),
                ))
            event = json.loads(path.read_text().strip())
        self.assertEqual(backend.calls, 1)
        self.assertEqual(event["attempt"], 1)
        self.assertTrue(result["terminal"])


if __name__ == "__main__":
    unittest.main()

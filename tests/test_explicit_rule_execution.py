from __future__ import annotations

import asyncio
import csv
import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emergent_specialization.explicit_rule_execution import (
    DEFAULT_CONFIG, EXPECTED_CONFIG, _validate_reservation, preflight, probes, prompt, report, run_real,
)
from emergent_specialization.models import BackendResponse


def response(answer: int = 0, *, model: str | None = "deepseek-v4-flash", cost: float | None = 0.000001,
             error: str | None = None, category: str | None = None, retryable: bool = True,
             retry_after: float | None = None) -> BackendResponse:
    metadata = {} if model is None else {"model": model, "system_fingerprint": "fake-fp"}
    return BackendResponse(None if error else json.dumps({"answer": answer, "confidence": 0.6}), 0.01,
                           token_usage=None if error else {"prompt_tokens": 10, "prompt_cache_hit_tokens": 0, "completion_tokens": 2},
                           error=error, error_category=category, retryable=retryable, retry_after_s=retry_after,
                           provider_metadata=metadata, observed_cost_usd=cost)


class FakeBackend:
    def __init__(self, handler): self.handler = handler; self.calls = 0; self.closed = False
    async def complete(self, **kwargs):
        index = self.calls; self.calls += 1; return self.handler(index, kwargs)
    async def close(self): self.closed = True


class ExplicitRuleExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.output = self.root / "raw"; self.report_dir = self.root / "report"; self.ledger = self.root / "cost_ledger.csv"
        self.reset_ledger()
    def reset_ledger(self):
        with self.ledger.open("w", newline="") as handle:
            writer = csv.writer(handle); writer.writerow(["session_id", "global_budget_usd", "spent_usd", "reserved_usd", "status", "updated_at_utc", "ar001_spent_usd", "ar001_reserved_usd"])
            writer.writerow(["autonomous-session-2026-08-08", "2.0", "0.0", "0.0", "open", "2026-08-08T13:40:02Z", "0.0", "0.0"])
    def tearDown(self): self.temp.cleanup()
    def run_experiment(self, backend, **kwargs):
        return asyncio.run(run_real(confirm_real=True, backend=backend, output_dir=self.output, ledger_path=self.ledger, sleep=kwargs.pop("sleep", self.no_sleep), **kwargs))
    async def no_sleep(self, _seconds): pass

    def test_frozen_config_probe_hash_count_and_balance(self):
        audit = preflight(ledger_path=self.ledger)
        self.assertEqual(audit["logical_calls"], 168); self.assertEqual(audit["probe_hash"], EXPECTED_CONFIG["probe_hash"])
        self.assertTrue(all(value == 2 for counts in audit["balance"].values() for value in counts.values()))
        bad = self.root / "bad.yaml"; bad.write_text(DEFAULT_CONFIG.read_text().replace("replicates: 3", "replicates: 4"))
        with self.assertRaisesRegex(ValueError, "frozen AR-001 config mismatch"): preflight(bad, ledger_path=self.ledger)

    def test_missing_or_unfunded_ledger_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "missing"): preflight(ledger_path=self.root / "absent.csv")
        text = self.ledger.read_text().replace(",0.0,0.0,open,", ",1.98,0.0,open,"); self.ledger.write_text(text)
        with self.assertRaisesRegex(RuntimeError, "experiment cap"): preflight(ledger_path=self.ledger)

    def test_prompt_has_matching_rule_and_no_memory_or_agent_id(self):
        text = prompt(probes(EXPECTED_CONFIG)[0]); self.assertIn("z=(2*x+1*y+1) mod 7", text)
        self.assertNotIn("memory", text.lower()); self.assertNotIn("agent_", text)

    def test_valid_wrong_and_ood_have_no_retry_resume_dedupes_and_report_is_complete(self):
        fake = FakeBackend(lambda i, _: response(7 if i == 0 else 6))
        manifest = self.run_experiment(fake)
        self.assertEqual(manifest["status"], "completed"); self.assertEqual(fake.calls, 168); self.assertTrue(fake.closed)
        second = FakeBackend(lambda _i, _k: response(0)); resumed = self.run_experiment(second)
        self.assertEqual(resumed["completed_logical_queries"], 168); self.assertEqual(second.calls, 0)
        result = report(output_dir=self.output, report_dir=self.report_dir)
        self.assertEqual(result["deduplicated_logical_successes"], 168); self.assertEqual(result["semantic_ood"], 1)
        self.assertEqual(result["health"], "complete"); self.assertEqual(len(result["agreement"]["tasks"]), 56)
        self.assertEqual(set(result["latency_s"]), {"mean", "median", "min", "max", "total"})
        self.assertIn("mean_pairwise_correctness", result["agreement"])

    def test_retry_after_is_bounded_and_technical_retry_occurs_once(self):
        delays = []
        async def record(value): delays.append(value)
        fake = FakeBackend(lambda i, _: response(error="transport", category="transient_transport", retry_after=99, model=None, cost=0.0) if i == 0 else response(0))
        manifest = self.run_experiment(fake, sleep=record)
        self.assertEqual(manifest["status"], "completed"); self.assertEqual(fake.calls, 169); self.assertEqual(delays, [30.0])
        events = [json.loads(x) for x in (self.output / "events.jsonl").read_text().splitlines()]
        self.assertEqual([events[0]["attempt"], events[1]["attempt"]], [0, 1])

    def test_nontechnical_error_does_not_retry_and_two_attempt_policy_is_durable(self):
        fake = FakeBackend(lambda _i, _k: response(error="bad request", category="invalid_parameters", retryable=True, model=None, cost=0.0))
        manifest = self.run_experiment(fake)
        self.assertEqual(fake.calls, 168); self.assertEqual(manifest["status"], "incomplete")
        again = FakeBackend(lambda _i, _k: response(0)); resumed = self.run_experiment(again)
        # A nontechnical failure is never retried, including after restart.
        self.assertEqual(again.calls, 0); self.assertEqual(resumed["status"], "incomplete")

    def test_model_missing_or_mismatch_and_missing_cost_fail_closed(self):
        for candidate, expected in ((None, "invalid_model"), ("other-model", "invalid_model")):
            with self.subTest(model=candidate):
                self.reset_ledger()
                out = self.root / str(candidate); backend = FakeBackend(lambda _i, _k, candidate=candidate: response(model=candidate))
                result = asyncio.run(run_real(confirm_real=True, backend=backend, output_dir=out, ledger_path=self.ledger, sleep=self.no_sleep))
                self.assertEqual(result["status"], expected); self.assertEqual(backend.calls, 1)
        self.reset_ledger(); out = self.root / "missing-cost"; backend = FakeBackend(lambda _i, _k: BackendResponse('{"answer": 0, "confidence": 0.5}', .01, provider_metadata={"model": "deepseek-v4-flash"}))
        result = asyncio.run(run_real(confirm_real=True, backend=backend, output_dir=out, ledger_path=self.ledger, sleep=self.no_sleep))
        self.assertEqual(result["status"], "failed"); self.assertEqual(backend.calls, 1)
        with self.ledger.open(newline="") as handle: ledger_row = next(csv.DictReader(handle))
        self.assertEqual(float(ledger_row["ar001_reserved_usd"]), EXPECTED_CONFIG["max_attempt_cost_reserve_usd"])
        resume = FakeBackend(lambda _i, _k: response(0)); resumed = asyncio.run(run_real(confirm_real=True, backend=resume, output_dir=out, ledger_path=self.ledger, sleep=self.no_sleep))
        self.assertEqual(resumed["status"], "failed"); self.assertEqual(resume.calls, 0); self.assertTrue(resume.closed)

    def test_cost_guard_and_attempt_cap(self):
        costly = FakeBackend(lambda _i, _k: response(cost=0.05))
        result = self.run_experiment(costly); self.assertEqual(result["status"], "budget_violation"); self.assertEqual(costly.calls, 1)
        # Fresh fixture: every logical receives exactly two retryable attempts (336 total).
        self.output = self.root / "attempt-cap"
        self.reset_ledger()
        retrying = FakeBackend(lambda _i, _k: response(error="transport", category="transport", model=None, cost=0.0))
        result = self.run_experiment(retrying); self.assertEqual(retrying.calls, 336); self.assertEqual(result["status"], "guard_stopped")

    def test_duplicate_success_is_invalid_and_manifest_precedes_credentials(self):
        fake = FakeBackend(lambda _i, _k: response(0)); self.run_experiment(fake)
        events = self.output / "events.jsonl"; first = events.read_text().splitlines()[0];
        with events.open("a") as handle: handle.write(first + "\n")
        result = self.run_experiment(FakeBackend(lambda _i, _k: response(0))); self.assertEqual(result["status"], "invalid_duplicate_success")
        fresh = self.root / "credential-failure"
        self.reset_ledger()
        with patch("emergent_specialization.explicit_rule_execution.CredentialStore.get", side_effect=RuntimeError("no credential")):
            result = asyncio.run(run_real(confirm_real=True, output_dir=fresh, ledger_path=self.ledger, sleep=self.no_sleep))
        self.assertEqual(result["status"], "failed"); manifest = json.loads((fresh / "manifest.json").read_text())
        self.assertIn("config_hash", manifest); self.assertIn("git_head", manifest)

    def test_resume_manifest_and_cost_reconciliation_fail_closed(self):
        self.run_experiment(FakeBackend(lambda _i, _k: response(0)))
        manifest_path = self.output / "manifest.json"; manifest = json.loads(manifest_path.read_text()); original = dict(manifest)
        manifest["config_hash"] = "tampered"; manifest_path.write_text(json.dumps(manifest))
        backend = FakeBackend(lambda _i, _k: response(0)); result = self.run_experiment(backend)
        self.assertEqual(result["status"], "failed"); self.assertEqual(backend.calls, 0); self.assertTrue(backend.closed)
        original["observed_cost_usd"] = 0.0; manifest_path.write_text(json.dumps(original))
        result = self.run_experiment(FakeBackend(lambda _i, _k: response(0)))
        self.assertIn("does not reconcile", result["failure"])
        original["observed_cost_usd"] = 168 * 0.000001; manifest_path.write_text(json.dumps(original))
        lines = self.ledger.read_text().splitlines(); fields = lines[0].split(","); values = lines[1].split(","); values[fields.index("ar001_spent_usd")] = "0.0"; self.ledger.write_text("\n".join([lines[0], ",".join(values)]) + "\n")
        result = self.run_experiment(FakeBackend(lambda _i, _k: response(0)))
        self.assertIn("ledger spent does not equal", result["failure"])

    def test_ledger_updates_preserve_extra_schema_and_history_rows(self):
        self.ledger.write_text("session_id,global_budget_usd,spent_usd,reserved_usd,status,updated_at_utc,ar001_spent_usd,ar001_reserved_usd,note\n"
                               "autonomous-session-2026-08-08,2.0,0.0,0.0,open,2026-08-08T13:40:02Z,0.0,0.0,keep\n"
                               "older-session,2.0,1.0,0.0,closed,2026-08-07T00:00:00Z,0.0,0.0,history\n")
        self.run_experiment(FakeBackend(lambda _i, _k: response(cost=0.05)))
        with self.ledger.open(newline="") as handle: rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["note"], "keep"); self.assertEqual(rows[1]["session_id"], "older-session"); self.assertEqual(rows[1]["note"], "history")

    def test_terminal_model_failure_blocks_resume_and_actual_over_bound_is_terminal(self):
        first = FakeBackend(lambda _i, _k: response(model="wrong")); result = self.run_experiment(first)
        self.assertEqual(result["status"], "invalid_model")
        later = FakeBackend(lambda _i, _k: response(0)); self.assertEqual(self.run_experiment(later)["status"], "invalid_model"); self.assertEqual(later.calls, 0)
        self.reset_ledger(); self.output = self.root / "over-reserve"; costly = FakeBackend(lambda _i, _k: response(cost=0.006))
        result = self.run_experiment(costly); self.assertEqual(result["status"], "budget_violation")
        with self.ledger.open(newline="") as handle: row = next(csv.DictReader(handle))
        self.assertEqual(float(row["ar001_spent_usd"]), 0.006); self.assertEqual(float(row["ar001_reserved_usd"]), 0.0)

    def test_reservation_is_demonstrated_and_rate_limit_is_not_whitelisted(self):
        upper = _validate_reservation(EXPECTED_CONFIG, probes(EXPECTED_CONFIG))
        self.assertLessEqual(upper, EXPECTED_CONFIG["max_attempt_cost_reserve_usd"])
        bad = dict(EXPECTED_CONFIG); bad["max_attempt_cost_reserve_usd"] = upper / 2
        with self.assertRaisesRegex(ValueError, "below"): _validate_reservation(bad, probes(EXPECTED_CONFIG))
        rate = FakeBackend(lambda _i, _k: response(error="rate", category="rate_limit", model=None, cost=0.0))
        result = self.run_experiment(rate); self.assertEqual(result["status"], "incomplete"); self.assertEqual(rate.calls, 168)

    def test_implementation_hash_is_resume_compatible_and_output_lock_is_exclusive(self):
        self.run_experiment(FakeBackend(lambda _i, _k: response(0)))
        manifest_path = self.output / "manifest.json"; manifest = json.loads(manifest_path.read_text()); self.assertIn("implementation_sha256", manifest)
        manifest["implementation_sha256"] = "changed"; manifest_path.write_text(json.dumps(manifest))
        resumed = self.run_experiment(FakeBackend(lambda _i, _k: response(0))); self.assertEqual(resumed["status"], "failed"); self.assertIn("implementation_sha256", resumed["failure"])
        self.reset_ledger(); locked_output = self.root / "locked"; locked_output.mkdir(); handle = (locked_output / ".execution.lock").open("a+"); fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        backend = FakeBackend(lambda _i, _k: response(0))
        try:
            with self.assertRaisesRegex(RuntimeError, "execution-locked"): asyncio.run(run_real(confirm_real=True, backend=backend, output_dir=locked_output, ledger_path=self.ledger, sleep=self.no_sleep))
        finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN); handle.close()
        self.assertEqual(backend.calls, 0); self.assertTrue(backend.closed)


if __name__ == "__main__": unittest.main()

from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.probes import generate_probe_payload, load_probe_set, write_probe_set


class ProbeTests(unittest.TestCase):
    def test_fixed_probe_payload_has_ten_tasks_per_world(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "probes.json"
            payload = generate_probe_payload(HiddenWorldEnvironment())
            write_probe_set(path, payload)
            tasks, digest = load_probe_set(path)
        self.assertEqual(digest, payload["content_sha256"])
        self.assertEqual(len(tasks), 40)
        self.assertEqual(Counter(task.world for task in tasks), {world: 10 for world in HiddenWorldEnvironment().worlds})

    def test_probe_hash_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "probes.json"
            payload = generate_probe_payload(HiddenWorldEnvironment())
            payload["tasks"][0]["x"] = 999
            write_probe_set(path, payload)
            with self.assertRaises(ValueError):
                load_probe_set(path)

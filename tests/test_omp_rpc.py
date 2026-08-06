from __future__ import annotations

import unittest

from emergent_specialization.providers.omp_rpc import OMPBackend


class OMPBackendTests(unittest.TestCase):
    def test_every_completion_uses_a_fresh_restricted_rpc_session(self) -> None:
        backend = OMPBackend(executable="omp", thinking="off")
        command = backend.command_for(system_prompt="same system prompt", model="deepseek/deepseek-v4-flash")
        for flag in (
            "--mode",
            "rpc",
            "--no-session",
            "--no-tools",
            "--no-lsp",
            "--no-pty",
            "--no-extensions",
            "--no-skills",
            "--no-rules",
        ):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--model") + 1], "deepseek/deepseek-v4-flash")
        self.assertEqual(command[command.index("--system-prompt") + 1], "same system prompt")

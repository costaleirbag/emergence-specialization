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

    def test_extracts_usage_from_nested_rpc_frames_without_assuming_frame_shape(self) -> None:
        usage = OMPBackend._extract_token_usage(
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 4,
                        "total_tokens": 16,
                    },
                },
            }
        )
        self.assertEqual(usage["prompt_tokens"], 12)
        self.assertEqual(usage["completion_tokens"], 4)
        self.assertEqual(usage["total_tokens"], 16)

    def test_usage_is_none_when_omp_does_not_expose_it(self) -> None:
        self.assertIsNone(OMPBackend._extract_token_usage({"type": "agent_end"}))

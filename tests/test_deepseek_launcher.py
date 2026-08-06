from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run-deepseek-experiment.sh"


class DeepSeekLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.log_path = self.root / "calls.log"
        self._write_fake_commands()

    def _write_executable(self, name: str, content: str) -> None:
        path = self.bin_dir / name
        path.write_text(textwrap.dedent(content), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _write_fake_commands(self) -> None:
        self._write_executable(
            "bw",
            """\
            #!/bin/sh
            set -eu
            printf '%s\\n' "$*" >> "$FAKE_LOG"
            case "$1" in
              status) printf '{"status":"%s"}\\n' "$FAKE_BW_STATUS" ;;
              unlock) printf '%s\\n' "fake-session" ;;
              sync) : ;;
              list) printf '%s\\n' "$FAKE_ITEMS_JSON" ;;
              get) printf '%s\\n' "fake-deepseek-key" ;;
              lock) : ;;
              *) exit 97 ;;
            esac
            """,
        )
        self._write_executable(
            "uv",
            """\
            #!/bin/sh
            set -eu
            if [ -n "${BW_SESSION:-}" ]; then
              printf '%s\\n' 'child_bw_session=present' >> "$FAKE_LOG"
              exit 71
            fi
            if [ "${DEEPSEEK_API_KEY:-}" != 'fake-deepseek-key' ]; then
              printf '%s\\n' 'child_deepseek_key=missing_or_wrong' >> "$FAKE_LOG"
              exit 72
            fi
            printf '%s\\n' 'uv_called child_bw_session=absent child_deepseek_key=present' >> "$FAKE_LOG"
            exit "${FAKE_UV_EXIT:-0}"
            """,
        )

    def _run_launcher(
        self,
        *,
        status: str = "locked",
        items: list[dict[str, str]] | None = None,
        uv_exit: int = 0,
        inherited_session: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.bin_dir}{os.pathsep}{environment['PATH']}",
                "FAKE_LOG": str(self.log_path),
                "FAKE_BW_STATUS": status,
                "FAKE_ITEMS_JSON": json.dumps(items if items is not None else [{"id": "item-1", "name": "DeepSeek API"}]),
                "FAKE_UV_EXIT": str(uv_exit),
            }
        )
        if inherited_session is None:
            environment.pop("BW_SESSION", None)
        else:
            environment["BW_SESSION"] = inherited_session
        return subprocess.run(
            [str(LAUNCHER), "--config", "configs/smoke_real_private.yaml"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _log_lines(self) -> list[str]:
        return self.log_path.read_text(encoding="utf-8").splitlines() if self.log_path.exists() else []

    def test_locked_vault_is_fetched_once_locked_before_experiment_and_not_inherited(self) -> None:
        result = self._run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._log_lines()
        self.assertEqual(lines.count("unlock --raw"), 1)
        self.assertIn("sync --session fake-session", lines)
        self.assertIn("get password item-1 --session fake-session", lines)
        self.assertEqual(lines.count("lock --session fake-session"), 1)
        self.assertIn("uv_called child_bw_session=absent child_deepseek_key=present", lines)
        self.assertLess(lines.index("lock --session fake-session"), lines.index("uv_called child_bw_session=absent child_deepseek_key=present"))
        self.assertNotIn("fake-deepseek-key", result.stdout + result.stderr)

    def test_unlocked_vault_reuses_session_but_does_not_pass_it_to_experiment(self) -> None:
        result = self._run_launcher(status="unlocked", inherited_session="inherited-session")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._log_lines()
        self.assertNotIn("unlock --raw", lines)
        self.assertIn("sync --session inherited-session", lines)
        self.assertIn("lock --session inherited-session", lines)
        self.assertIn("uv_called child_bw_session=absent child_deepseek_key=present", lines)

    def test_unauthenticated_vault_does_not_start_experiment(self) -> None:
        result = self._run_launcher(status="unauthenticated")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unauthenticated", result.stderr)
        self.assertNotIn("uv_called", self._log_lines())

    def test_missing_or_ambiguous_exact_item_rejects_before_experiment(self) -> None:
        for items in ([], [{"id": "one", "name": "DeepSeek API"}, {"id": "two", "name": "DeepSeek API"}]):
            with self.subTest(items=items):
                self.log_path.unlink(missing_ok=True)
                result = self._run_launcher(items=items)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Expected exactly one Bitwarden item", result.stderr)
                lines = self._log_lines()
                self.assertNotIn("uv_called child_bw_session=absent child_deepseek_key=present", lines)
                self.assertIn("lock --session fake-session", lines)

    def test_experiment_exit_code_is_preserved_and_cleanup_runs(self) -> None:
        result = self._run_launcher(uv_exit=23)
        self.assertEqual(result.returncode, 23)
        lines = self._log_lines()
        self.assertIn("uv_called child_bw_session=absent child_deepseek_key=present", lines)
        self.assertEqual(lines.count("lock --session fake-session"), 1)

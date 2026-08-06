"""Stateless OMP JSONL/RPC adapter.

Each completion starts a fresh ``omp --mode rpc --no-session`` process.  This
is intentionally less efficient than a long-lived agent session, but prevents
OMP's conversational history, compaction, and summaries from becoming an
uncontrolled experimental variable.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from ..models import BackendResponse


class OMPBackend:
    def __init__(
        self,
        *,
        executable: str = "omp",
        timeout_s: float = 120.0,
        thinking: str = "off",
        working_directory: str | None = None,
    ) -> None:
        self.executable = executable
        self.timeout_s = timeout_s
        self.thinking = thinking
        self.working_directory = working_directory

    def metadata(self) -> dict[str, Any]:
        version = "unavailable"
        try:
            result = subprocess.run(
                [self.executable, "--version"], text=True, capture_output=True, check=False, timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
            else:
                version = f"unavailable (exit {result.returncode})"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return {
            "backend": "omp_rpc",
            "executable": self.executable,
            "omp_version": version,
            "timeout_s": self.timeout_s,
            "thinking": self.thinking,
            "session_policy": "one fresh --mode rpc --no-session process per completion",
            "disabled_omp_features": [
                "tools",
                "skills",
                "rules",
                "extensions",
                "lsp",
                "pty",
                "session persistence",
            ],
            "decoding_note": (
                "OMP 17.2.10 CLI/RPC exposes model and thinking level but no documented "
                "temperature/top-p/max-tokens controls. All experimental calls receive the "
                "same available OMP arguments."
            ),
            "runtime_caveat": (
                "In a no-prompt local smoke test, OMP 17.2.10 still emitted an autoresearch "
                "extension UI widget frame despite --no-extensions. --no-tools prevents model "
                "tool use, but this built-in UI extension should be audited/disabled in OMP "
                "before treating a real run as a fully feature-free baseline."
            ),
        }

    def command_for(self, *, system_prompt: str, model: str) -> list[str]:
        """Expose the fixed, auditable command construction for tests/log review."""
        return [
            self.executable,
            "--mode",
            "rpc",
            "--no-session",
            "--model",
            model,
            "--system-prompt",
            system_prompt,
            "--no-tools",
            "--no-lsp",
            "--no-pty",
            "--no-extensions",
            "--no-skills",
            "--no-rules",
            "--no-title",
            "--thinking",
            self.thinking,
        ]

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        model_parameters: dict[str, Any],
    ) -> BackendResponse:
        started = time.perf_counter()
        command = self.command_for(system_prompt=system_prompt, model=model)
        cwd = str(Path(self.working_directory).resolve()) if self.working_directory else None
        stderr_parts: list[str] = []
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            raw = await asyncio.wait_for(
                self._run_rpc_turn(process, user_prompt, stderr_parts), timeout=self.timeout_s
            )
            response_text, token_usage = raw
            return BackendResponse(
                raw_response=response_text,
                latency_s=time.perf_counter() - started,
                token_usage=token_usage,
            )
        except TimeoutError:
            return BackendResponse(
                raw_response=None,
                latency_s=time.perf_counter() - started,
                error=f"OMP RPC timeout after {self.timeout_s:.1f}s",
            )
        except FileNotFoundError:
            return BackendResponse(
                raw_response=None,
                latency_s=time.perf_counter() - started,
                error=f"OMP executable not found: {self.executable!r}",
            )
        except Exception as exc:  # pragma: no cover - subprocess boundary
            detail = "".join(stderr_parts).strip()
            suffix = f" stderr={detail[-1000:]}" if detail else ""
            return BackendResponse(
                raw_response=None,
                latency_s=time.perf_counter() - started,
                error=f"OMP RPC failure: {type(exc).__name__}: {exc}{suffix}",
            )

    async def _run_rpc_turn(
        self,
        process: asyncio.subprocess.Process,
        user_prompt: str,
        stderr_parts: list[str],
    ) -> tuple[str, dict[str, Any] | None]:
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None

        async def drain_stderr() -> None:
            while line := await process.stderr.readline():
                stderr_parts.append(line.decode("utf-8", errors="replace"))

        stderr_task = asyncio.create_task(drain_stderr())
        assistant_text: str | None = None
        token_usage: dict[str, Any] | None = None
        try:
            ready = await self._read_frame(process.stdout)
            if ready.get("type") != "ready":
                raise RuntimeError(f"OMP did not emit RPC ready frame: {ready}")
            process.stdin.write(
                (json.dumps({"id": "prompt-1", "type": "prompt", "message": user_prompt}) + "\n").encode()
            )
            await process.stdin.drain()

            while True:
                frame = await self._read_frame(process.stdout)
                frame_usage = self._extract_token_usage(frame)
                if frame_usage is not None:
                    # OMP may emit a usage snapshot more than once. Keep the
                    # latest values without summing cumulative snapshots.
                    token_usage = {**(token_usage or {}), **frame_usage}
                frame_type = frame.get("type")
                if frame_type == "message_end":
                    candidate = self._extract_assistant_text(frame)
                    if candidate:
                        assistant_text = candidate
                elif frame_type == "response" and not frame.get("success", False):
                    raise RuntimeError(f"OMP RPC command error: {frame.get('error', 'unknown error')}")
                elif frame_type == "agent_end":
                    if assistant_text is None:
                        raise RuntimeError("OMP agent completed without an assistant text message")
                    return assistant_text, token_usage
        finally:
            if not process.stdin.is_closing():
                process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:  # pragma: no cover - defensive cleanup
                process.kill()
                await process.wait()
            await stderr_task

    @staticmethod
    async def _read_frame(stdout: asyncio.StreamReader) -> dict[str, Any]:
        line = await stdout.readline()
        if not line:
            raise RuntimeError("OMP RPC closed stdout before completing the request")
        try:
            frame = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSONL frame from OMP RPC: {line[:200]!r}") from exc
        if not isinstance(frame, dict):
            raise RuntimeError("OMP RPC frame is not an object")
        return frame

    @staticmethod
    def _extract_assistant_text(frame: dict[str, Any]) -> str | None:
        """Extract final assistant text across OMP's event payload variants."""
        candidates: list[str] = []

        def visit(value: Any, parent_role: str | None = None) -> None:
            if isinstance(value, dict):
                role = value.get("role", parent_role)
                if role == "assistant" and isinstance(value.get("text"), str):
                    candidates.append(value["text"])
                content = value.get("content")
                if role == "assistant" and isinstance(content, str):
                    candidates.append(content)
                if role == "assistant" and isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                            candidates.append(item["text"])
                for child in value.values():
                    visit(child, role)
            elif isinstance(value, list):
                for child in value:
                    visit(child, parent_role)

        visit(frame)
        return candidates[-1] if candidates else None

    @staticmethod
    def _extract_token_usage(frame: dict[str, Any]) -> dict[str, Any] | None:
        """Find a provider usage object without assuming one OMP frame shape."""
        usage_keys = {"input_tokens", "prompt_tokens", "output_tokens", "completion_tokens", "total_tokens",
                      "inputTokens", "promptTokens", "outputTokens", "completionTokens", "totalTokens"}
        candidates: list[dict[str, Any]] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key in ("usage", "token_usage", "tokenUsage"):
                    nested = value.get(key)
                    if isinstance(nested, dict):
                        candidates.append(nested)
                if usage_keys.intersection(value):
                    candidates.append(value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(frame)
        return dict(candidates[-1]) if candidates else None

"""Minimal provider boundary for controlled experimental inference."""

from __future__ import annotations

from typing import Any, Protocol

from ..models import BackendResponse


class LLMBackend(Protocol):
    """A stateless completion interface.

    The caller supplies the complete system and user context for every call. A
    backend must not be used as a source of scientific agent memory.
    """

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        model_parameters: dict[str, Any],
    ) -> BackendResponse: ...

    def metadata(self) -> dict[str, Any]: ...

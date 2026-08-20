"""Direct OpenAI-compatible DeepSeek API adapter.

This adapter performs exactly one HTTP completion per ``complete`` call. Retry
classification and backoff are owned by the experiment runtime, not by the
OpenAI SDK (``max_retries=0``).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any

from ..models import BackendResponse


RETRYABLE_STATUS_CODES = {429, 500, 503}
NON_RETRYABLE_STATUS_CODES = {400, 401, 402, 422}


def _status_code(exc: BaseException) -> int | None:
    value = getattr(exc, "status_code", None)
    if isinstance(value, int):
        return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _retry_after(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or getattr(exc, "headers", None)
    if not isinstance(headers, Mapping):
        return None
    value = headers.get("retry-after") or headers.get("Retry-After")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def classify_exception(exc: BaseException) -> tuple[str, bool, int | None, float | None]:
    status = _status_code(exc)
    if status in NON_RETRYABLE_STATUS_CODES:
        category = {
            400: "invalid_format",
            401: "authentication_failure",
            402: "insufficient_balance",
            422: "invalid_parameters",
        }[status]
        return category, False, status, None
    if status in RETRYABLE_STATUS_CODES:
        return {429: "rate_limit", 500: "server_error", 503: "overloaded"}[status], True, status, _retry_after(exc)
    name = type(exc).__name__.lower()
    if any(marker in name for marker in ("timeout", "connection", "connect", "network", "transport", "remoteprotocol", "readerror", "writeerror", "pool")):
        return "transient_transport", True, status, _retry_after(exc)
    return "provider_error", True, status, _retry_after(exc)


def _object_to_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dict(dumped) if isinstance(dumped, Mapping) else None
    return None


class DeepSeekDirectBackend:
    """Long-lived async client for stateless DeepSeek Chat Completions."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        thinking: str = "off",
        max_tokens: int = 128,
        connect_timeout_s: float = 10.0,
        read_timeout_s: float = 600.0,
        request_timeout_s: float = 660.0,
        pool_timeout_s: float = 10.0,
        user_id: str = "emergence-specialization",
        max_connections: int | None = None,
        max_keepalive_connections: int | None = None,
        credential_source: str = "keychain",
        client: Any | None = None,
        http_client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key must be supplied in memory")
        if thinking not in {"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto"}:
            raise ValueError("DeepSeek Direct thinking must be 'off' or a documented reasoning level")
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        self._api_key = api_key
        self.base_url = base_url
        self.thinking = thinking
        self.max_tokens = max_tokens
        self.connect_timeout_s = connect_timeout_s
        self.read_timeout_s = read_timeout_s
        self.request_timeout_s = request_timeout_s
        self.pool_timeout_s = pool_timeout_s
        self.user_id = user_id
        self.credential_source = credential_source
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self._owned_http_client = None
        if client is not None:
            self.client = client
        else:
            try:
                import httpx
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - dependency boundary
                raise RuntimeError("DeepSeek Direct requires the 'openai' and 'httpx' packages") from exc
            timeout = httpx.Timeout(
                timeout=request_timeout_s,
                connect=connect_timeout_s,
                read=read_timeout_s,
                write=request_timeout_s,
                pool=pool_timeout_s,
            )
            limits = httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            )
            if http_client is None:
                http_client = httpx.AsyncClient(timeout=timeout, limits=limits)
                self._owned_http_client = http_client
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=0,
                timeout=timeout,
                http_client=http_client,
            )

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "deepseek_direct",
            "base_url": self.base_url,
            "credential_source": self.credential_source,
            "sdk_max_retries": 0,
            "thinking": "disabled" if self.thinking == "off" else "enabled",
            "reasoning_effort": None if self.thinking == "off" else ("max" if self.thinking in {"xhigh", "max"} else "high"),
            "stream": False,
            "response_format": {"type": "json_object"},
            "user_id": self.user_id,
            "timeout_policy": {
                "connect_s": self.connect_timeout_s,
                "read_inactivity_s": self.read_timeout_s,
                "absolute_request_s": self.request_timeout_s,
                "pool_s": self.pool_timeout_s,
            },
            "client_limits": {
                "max_connections": self.max_connections,
                "max_keepalive_connections": self.max_keepalive_connections,
            },
            "max_tokens": self.max_tokens,
            "provider_sampling_seed_control": "unavailable",
        }

    async def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            result = close()
            if hasattr(result, "__await__"):
                await result
        elif self._owned_http_client is not None:
            await self._owned_http_client.aclose()

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        model_parameters: dict[str, Any],
    ) -> BackendResponse:
        started = time.perf_counter()
        thinking = str(model_parameters.get("thinking") or self.thinking)
        enabled = thinking != "off"
        request = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": int(model_parameters.get("max_tokens") or self.max_tokens),
            "stream": False,
            "extra_body": {"thinking": {"type": "enabled" if enabled else "disabled"}, "user_id": self.user_id},
        }
        if enabled:
            request["reasoning_effort"] = "max" if thinking in {"xhigh", "max"} else "high"
        try:
            response = await self.client.chat.completions.create(**request)
        except Exception as exc:  # provider/transport boundary
            category, retryable, status, retry_after = classify_exception(exc)
            return BackendResponse(
                raw_response=None,
                latency_s=time.perf_counter() - started,
                error=f"DeepSeek Direct {category}",
                error_category=category,
                retryable=retryable,
                http_status=status,
                retry_after_s=retry_after,
            )

        choices = getattr(response, "choices", None) or []
        message = getattr(choices[0], "message", None) if choices else None
        content = getattr(message, "content", None) if message is not None else None
        usage = _object_to_dict(getattr(response, "usage", None))
        provider_metadata = {
            "id": getattr(response, "id", None),
            "model": getattr(response, "model", None),
            "system_fingerprint": getattr(response, "system_fingerprint", None),
            "request_id": getattr(response, "_request_id", None),
        }
        provider_metadata = {key: value for key, value in provider_metadata.items() if value is not None}
        if not isinstance(content, str) or not content.strip():
            return BackendResponse(
                raw_response=None,
                latency_s=time.perf_counter() - started,
                token_usage=usage,
                error="DeepSeek Direct empty content",
                error_category="empty_content",
                retryable=True,
                provider_metadata=provider_metadata,
            )
        return BackendResponse(
            raw_response=content,
            latency_s=time.perf_counter() - started,
            token_usage=usage,
            provider_metadata=provider_metadata,
        )

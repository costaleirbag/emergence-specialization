from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from emergent_specialization.providers.deepseek_direct import DeepSeekDirectBackend, classify_exception


class FakeCompletions:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None) -> None:
        completions = FakeCompletions(response, error)
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class ErrorWithStatus(Exception):
    def __init__(self, status_code: int, retry_after: str | None = None) -> None:
        self.status_code = status_code
        self.response = SimpleNamespace(status_code=status_code, headers={"Retry-After": retry_after} if retry_after else {})


class Usage:
    def model_dump(self):
        return {
            "prompt_tokens": 100,
            "completion_tokens": 4,
            "total_tokens": 104,
            "prompt_tokens_details": {"cached_tokens": 80},
            "completion_tokens_details": {"reasoning_tokens": 0},
        }


class DirectBackendTests(unittest.TestCase):
    def test_thinking_enabled_uses_same_model_documented_toggle(self) -> None:
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer": 4, "confidence": 0.73}', reasoning_content="not persisted"))],
            usage=Usage(), id="resp-thinking", model="deepseek-v4-flash", system_fingerprint="fp-1", _request_id="req-1",
        )
        client = FakeClient(response=response)
        backend = DeepSeekDirectBackend(api_key="secret-never-logged", thinking="high", client=client)
        result = asyncio.run(backend.complete(system_prompt="json", user_prompt="json", model="deepseek-v4-flash", model_parameters={"thinking": "high", "max_tokens": 128}))
        self.assertIsNone(result.error)
        self.assertEqual(client.chat.completions.kwargs["extra_body"]["thinking"], {"type": "enabled"})
        self.assertEqual(client.chat.completions.kwargs["reasoning_effort"], "high")
        self.assertEqual(backend.metadata()["thinking"], "enabled")

    def test_success_uses_documented_stateless_json_request(self) -> None:
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer": 4, "confidence": 0.73}'))],
            usage=Usage(),
            id="resp-1",
            model="deepseek-v4-flash",
            system_fingerprint="fp-1",
            _request_id="req-1",
        )
        client = FakeClient(response=response)
        backend = DeepSeekDirectBackend(api_key="secret-never-logged", client=client)
        result = asyncio.run(
            backend.complete(
                system_prompt="Return JSON.",
                user_prompt="{\"answer\": 4, \"confidence\": 0.73}",
                model="deepseek-v4-flash",
                model_parameters={"max_tokens": 128},
            )
        )
        request = client.chat.completions.kwargs
        self.assertEqual(result.raw_response, '{"answer": 4, "confidence": 0.73}')
        self.assertEqual(result.token_usage["prompt_tokens"], 100)
        self.assertEqual(request["model"], "deepseek-v4-flash")
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertFalse(request["stream"])
        self.assertEqual(request["extra_body"]["thinking"], {"type": "disabled"})
        self.assertEqual(request["extra_body"]["user_id"], "emergence-specialization")
        self.assertEqual(backend.metadata()["sdk_max_retries"], 0)
        self.assertNotIn("secret-never-logged", repr(backend.metadata()))

    def test_empty_content_is_retryable(self) -> None:
        client = FakeClient(response=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))], usage=None))
        result = asyncio.run(
            DeepSeekDirectBackend(api_key="secret", client=client).complete(
                system_prompt="json", user_prompt="json", model="deepseek-v4-flash", model_parameters={}
            )
        )
        self.assertEqual(result.error_category, "empty_content")
        self.assertTrue(result.retryable)

    def test_error_matrix(self) -> None:
        self.assertEqual(classify_exception(ErrorWithStatus(400))[:2], ("invalid_format", False))
        self.assertEqual(classify_exception(ErrorWithStatus(401))[:2], ("authentication_failure", False))
        self.assertEqual(classify_exception(ErrorWithStatus(402))[:2], ("insufficient_balance", False))
        self.assertEqual(classify_exception(ErrorWithStatus(422))[:2], ("invalid_parameters", False))
        category, retryable, status, retry_after = classify_exception(ErrorWithStatus(429, "3"))
        self.assertEqual((category, retryable, status, retry_after), ("rate_limit", True, 429, 3.0))
        self.assertEqual(classify_exception(ErrorWithStatus(500))[:2], ("server_error", True))
        self.assertEqual(classify_exception(ErrorWithStatus(503))[:2], ("overloaded", True))
        category, retryable, _, _ = classify_exception(TimeoutError())
        self.assertEqual((category, retryable), ("transient_transport", True))

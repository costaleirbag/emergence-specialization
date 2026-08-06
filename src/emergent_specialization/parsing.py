"""Strict, logged parsing of the answer/confidence contract."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedOutput:
    answer: int
    confidence: float


class ResponseParseError(ValueError):
    pass


def parse_agent_output(raw: str) -> ParsedOutput:
    """Parse a JSON answer object; never repair or invent an answer.

    The system prompt asks for raw JSON, but this accepts a harmless prose or
    Markdown wrapper by locating one decodable object. Schema/type/range checks
    remain strict, and any ambiguity is logged as a parse failure.
    """
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        start = raw.find("{")
        if start < 0:
            raise ResponseParseError(f"invalid JSON: {exc.msg}") from exc
        try:
            value, _ = json.JSONDecoder().raw_decode(raw[start:])
        except json.JSONDecodeError as nested_exc:
            raise ResponseParseError(f"invalid JSON: {nested_exc.msg}") from nested_exc
    if not isinstance(value, dict):
        raise ResponseParseError("response must be a JSON object")
    if set(value) != {"answer", "confidence"}:
        raise ResponseParseError("response must contain exactly answer and confidence")
    answer = value["answer"]
    confidence = value["confidence"]
    if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer <= 6:
        raise ResponseParseError("answer must be an integer from 0 through 6")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ResponseParseError("confidence must be a numeric value")
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        raise ResponseParseError("confidence must lie in [0, 1]")
    return ParsedOutput(answer=answer, confidence=confidence)

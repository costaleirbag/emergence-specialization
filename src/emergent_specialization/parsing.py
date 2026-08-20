"""Strict, logged parsing of the answer/confidence contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class ParsedOutput:
    answer: int
    confidence: float
    answer_in_domain: bool
    semantic_violation: str | None = None


class ResponseParseError(ValueError):
    pass


def parse_agent_output(raw: str) -> ParsedOutput:
    """Extract the last valid answer object without repairing model output.

    Models occasionally put prose, set notation, or multiple fenced/object
    fragments before their final answer. We scan balanced brace-delimited
    candidates (respecting quoted strings), validate each candidate strictly,
    and choose the last valid ``AgentResponse`` object.  Syntax/schema validity
    is deliberately separate from task-domain validity: an integer answer such
    as ``7`` is a scientifically incorrect answer, not an unreadable response.
    Only malformed objects or invalid confidence values remain parse failures.
    """
    candidates: list[ParsedOutput] = []
    direct = _try_parse_object(raw.strip())
    if direct is not None:
        candidates.append(direct)
    for fragment in _balanced_object_fragments(raw):
        parsed = _try_parse_object(fragment)
        if parsed is not None:
            candidates.append(parsed)
    if not candidates:
        raise ResponseParseError("no valid answer/confidence JSON object found")
    return candidates[-1]


def _try_parse_object(fragment: str) -> ParsedOutput | None:
    try:
        value: Any = json.loads(fragment)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(value, dict) or set(value) != {"answer", "confidence"}:
        return None
    answer = value["answer"]
    confidence = value["confidence"]
    if isinstance(answer, bool) or not isinstance(answer, int):
        return None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        return None
    answer_in_domain = 0 <= answer <= 6
    return ParsedOutput(
        answer=answer,
        confidence=confidence,
        answer_in_domain=answer_in_domain,
        semantic_violation=None if answer_in_domain else "answer_out_of_domain",
    )


def _balanced_object_fragments(raw: str) -> Iterator[str]:
    """Yield every balanced ``{...}`` fragment in source order.

    This is deliberately a small scanner rather than a regex: braces inside
    JSON strings do not affect balance, and malformed prose fragments cannot
    prevent a later valid object from being considered.
    """
    decoder = json.JSONDecoder()
    for start, char in enumerate(raw):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for end in range(start, len(raw)):
            current = raw[end]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    fragment = raw[start : end + 1]
                    # Validate syntax here only to avoid yielding a malformed
                    # outer fragment that swallowed a later valid object.
                    try:
                        decoder.raw_decode(fragment)
                    except json.JSONDecodeError:
                        pass
                    yield fragment
                    break

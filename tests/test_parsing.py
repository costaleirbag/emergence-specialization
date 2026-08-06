from __future__ import annotations

import unittest

from emergent_specialization.parsing import ResponseParseError, parse_agent_output


class ParsingTests(unittest.TestCase):
    def test_accepts_exact_schema(self) -> None:
        result = parse_agent_output('{"answer": 3, "confidence": 0.75}')
        self.assertEqual(result.answer, 3)
        self.assertEqual(result.confidence, 0.75)

    def test_accepts_json_in_markdown_wrapper_but_validates_it(self) -> None:
        result = parse_agent_output("```json\n{\"answer\": 1, \"confidence\": 1}\n```")
        self.assertEqual(result.answer, 1)
        self.assertEqual(result.confidence, 1.0)

    def test_never_repairs_an_invalid_answer(self) -> None:
        with self.assertRaises(ResponseParseError):
            parse_agent_output('{"answer": 9, "confidence": 0.5}')

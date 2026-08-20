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

    def test_accepts_prose_before_json(self) -> None:
        result = parse_agent_output('I considered several candidates. Final: {"answer": 5, "confidence": 0.05}')
        self.assertEqual((result.answer, result.confidence), (5, 0.05))

    def test_ignores_set_notation_before_valid_json(self) -> None:
        result = parse_agent_output('Candidates were {0,1,3,5,6}. Final: {"answer":5,"confidence":0.05}')
        self.assertEqual((result.answer, result.confidence), (5, 0.05))

    def test_selects_only_object_matching_agent_response_schema(self) -> None:
        result = parse_agent_output(
            'Intermediate: {"answer": 4, "confidence": 0.8, "note": "discard"}. '
            'Final: {"answer": 2, "confidence": 0.81}'
        )
        self.assertEqual((result.answer, result.confidence), (2, 0.81))

    def test_selects_last_valid_object_deterministically(self) -> None:
        result = parse_agent_output(
            '{"answer": 1, "confidence": 0.2}\n'
            'Revision: {"answer": 6, "confidence": 0.9}'
        )
        self.assertEqual((result.answer, result.confidence), (6, 0.9))

    def test_accepts_out_of_domain_answer_as_scientific_failure(self) -> None:
        result = parse_agent_output('{"answer": 7, "confidence": 0.2}')
        self.assertEqual(result.answer, 7)
        self.assertFalse(result.answer_in_domain)
        self.assertEqual(result.semantic_violation, "answer_out_of_domain")

    def test_does_not_repair_out_of_domain_answer(self) -> None:
        result = parse_agent_output('{"answer": 9, "confidence": 0.5}')
        self.assertEqual(result.answer, 9)
        self.assertFalse(result.answer_in_domain)

    def test_rejects_confidence_outside_range(self) -> None:
        with self.assertRaises(ResponseParseError):
            parse_agent_output('Result: {"answer": 4, "confidence": 1.01}')

    def test_rejects_missing_fields(self) -> None:
        with self.assertRaises(ResponseParseError):
            parse_agent_output('Result: {"answer": 4}')

    def test_rejects_non_object_json(self) -> None:
        with self.assertRaises(ResponseParseError):
            parse_agent_output("[1, 2, 3]")

    def test_rejects_response_without_any_valid_json_object(self) -> None:
        with self.assertRaises(ResponseParseError):
            parse_agent_output("No structured answer was produced; candidates were {0,1,2}.")

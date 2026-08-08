from __future__ import annotations

import unittest

from emergent_specialization.environment import HIDDEN_RULES, HiddenWorldEnvironment
from emergent_specialization.gf7 import affine_rank, evaluate, solve_affine
from emergent_specialization.hidden_rule_identifiability import _context_key


def _observations(coefficients: tuple[int, int, int], points: list[tuple[int, int]]) -> list[tuple[int, int, int]]:
    return [(x, y, evaluate(coefficients, x, y)) for x, y in points]


class GF7Tests(unittest.TestCase):
    def test_alpha_recovery(self) -> None:
        observations = _observations(HIDDEN_RULES["ALPHA"], [(0, 0), (1, 0), (0, 1)])
        result = solve_affine(observations)
        self.assertEqual(result.status, "unique")
        self.assertEqual(result.coefficients, HIDDEN_RULES["ALPHA"])
        self.assertEqual(result.candidate_count, 1)


    def test_modular_aliases_are_one_design_row(self) -> None:
        self.assertEqual(affine_rank([(4, 5), (11, 12)]), 1)


    def test_two_distinct_rows_have_seven_candidates(self) -> None:
        result = solve_affine(_observations(HIDDEN_RULES["ALPHA"], [(0, 0), (1, 0)]))
        self.assertEqual((result.status, result.rank, result.candidate_count), ("underdetermined", 2, 7))


    def test_collinear_points_have_rank_two(self) -> None:
        self.assertEqual(affine_rank([(0, 0), (1, 1), (2, 2)]), 2)


    def test_contradictory_extra_label_is_inconsistent(self) -> None:
        observations = _observations(HIDDEN_RULES["ALPHA"], [(0, 0), (1, 0), (0, 1)])
        observations.append((0, 0, (observations[0][2] + 1) % 7))
        result = solve_affine(observations)
        self.assertEqual((result.status, result.candidate_count), ("inconsistent", 0))


    def test_systematic_plus_one_recovers_shifted_intercept(self) -> None:
        observations = [(x, y, (z + 1) % 7) for x, y, z in _observations(HIDDEN_RULES["ALPHA"], [(0, 0), (1, 0), (0, 1)])]
        self.assertEqual(solve_affine(observations).coefficients, (2, 1, 2))


    def test_permutation_invariance(self) -> None:
        observations = _observations(HIDDEN_RULES["ALPHA"], [(0, 0), (1, 0), (0, 1), (2, 3)])
        self.assertEqual(solve_affine(observations), solve_affine(list(reversed(observations))))


    def test_truthful_full_rank_symbolic_probe_accuracy_is_one(self) -> None:
        environment = HiddenWorldEnvironment(); coefficients = HIDDEN_RULES["ALPHA"]
        result = solve_affine(_observations(coefficients, [(0, 0), (1, 0), (0, 1)]))
        probes = [(x, y) for x in range(7) for y in range(7)]
        self.assertIsNotNone(result.coefficients)
        self.assertEqual(sum(evaluate(result.coefficients, x, y) == environment.answer_for("ALPHA", x, y) for x, y in probes) / len(probes), 1.0)

    def test_audit_context_key_separates_reasoning_modes(self) -> None:
        event = {"context": {"world": "ALPHA", "k": 0}, "reasoning": "off"}
        high = {**event, "reasoning": "high"}
        self.assertNotEqual(_context_key(event), _context_key(high))

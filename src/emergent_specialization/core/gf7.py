"""Exact affine-rule linear algebra over the finite field GF(7).

Rules are represented as ``(a, b, c)`` for ``z = a*x + b*y + c (mod 7)``.
All public functions normalize integer inputs modulo seven.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

MODULUS = 7
SolveStatus = Literal["unique", "underdetermined", "inconsistent"]


def _mod(value: int) -> int:
    return int(value) % MODULUS


def affine_row(x: int, y: int) -> tuple[int, int, int]:
    """Return the GF(7) design row ``[x, y, 1]``."""
    return (_mod(x), _mod(y), 1)


def rank(rows: Iterable[Iterable[int]]) -> int:
    """Compute matrix rank exactly using Gaussian elimination in GF(7)."""
    matrix = [[_mod(value) for value in row] for row in rows]
    if not matrix:
        return 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("all rows must have equal width")
    pivot_row = 0
    for column in range(width):
        pivot = next((index for index in range(pivot_row, len(matrix)) if matrix[index][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        inverse = pow(matrix[pivot_row][column], -1, MODULUS)
        matrix[pivot_row] = [value * inverse % MODULUS for value in matrix[pivot_row]]
        for index in range(len(matrix)):
            if index == pivot_row:
                continue
            factor = matrix[index][column]
            if factor:
                matrix[index] = [(value - factor * base) % MODULUS for value, base in zip(matrix[index], matrix[pivot_row])]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row


def affine_rank(observations: Iterable[tuple[int, int, int] | tuple[int, int]]) -> int:
    """Rank the affine design rows for observations (labels are ignored)."""
    return rank(affine_row(item[0], item[1]) for item in observations)


@dataclass(frozen=True)
class AffineSolve:
    status: SolveStatus
    rank: int
    coefficients: tuple[int, int, int] | None
    candidate_count: int


def solve_affine(observations: Iterable[tuple[int, int, int]]) -> AffineSolve:
    """Solve labelled affine observations exactly over GF(7)."""
    matrix = [[*affine_row(x, y), _mod(z)] for x, y, z in observations]
    pivot_row = 0
    pivots: list[int] = []
    for column in range(3):
        pivot = next((index for index in range(pivot_row, len(matrix)) if matrix[index][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        inverse = pow(matrix[pivot_row][column], -1, MODULUS)
        matrix[pivot_row] = [value * inverse % MODULUS for value in matrix[pivot_row]]
        for index in range(len(matrix)):
            if index == pivot_row:
                continue
            factor = matrix[index][column]
            if factor:
                matrix[index] = [(value - factor * base) % MODULUS for value, base in zip(matrix[index], matrix[pivot_row])]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    if any(not any(row[:3]) and row[3] for row in matrix):
        return AffineSolve("inconsistent", len(pivots), None, 0)
    if len(pivots) < 3:
        return AffineSolve("underdetermined", len(pivots), None, MODULUS ** (3 - len(pivots)))
    coefficients = [0, 0, 0]
    for row, column in enumerate(pivots):
        coefficients[column] = matrix[row][3]
    return AffineSolve("unique", 3, tuple(coefficients), 1)


def evaluate(coefficients: tuple[int, int, int], x: int, y: int) -> int:
    """Evaluate an affine GF(7) rule."""
    a, b, c = coefficients
    return _mod(a * x + b * y + c)

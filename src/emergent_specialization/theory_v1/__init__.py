"""Deterministic Theory V1 mathematics and prospective protocol helpers.

This package is intentionally independent of the society runner.  It can build
sealed manifests and validate the frozen effective model without contacting a
provider.  Paid micro/macro execution is not implicit in any import.
"""

from .dynamics import (
    centered_projector,
    competence_interaction,
    critical_beta,
    jacobian,
    retention,
    spectral_summary,
    transfer_operator,
)

__all__ = [
    "centered_projector",
    "competence_interaction",
    "critical_beta",
    "jacobian",
    "retention",
    "spectral_summary",
    "transfer_operator",
]

"""Permutation-invariant diagnostics for behavioral differentiation."""

from emergent_specialization.metrics.behavioral import behavioral_cosine_distance, competence_matrix, individual_accuracy
from emergent_specialization.metrics.complementarity import complementarity_metrics
from emergent_specialization.metrics.differentiation import (
    competence_differentiation_phi,
    competence_differentiation_phi_from_mapping,
    division_of_labor_matching,
    routing_alignment,
)
from emergent_specialization.metrics.hse import hierarchic_social_entropy
from emergent_specialization.metrics.information import mutual_information, normalized_utilization_entropy, utilization_entropy

__all__ = [
    "behavioral_cosine_distance",
    "competence_matrix",
    "individual_accuracy",
    "complementarity_metrics",
    "competence_differentiation_phi",
    "competence_differentiation_phi_from_mapping",
    "routing_alignment",
    "division_of_labor_matching",
    "hierarchic_social_entropy",
    "mutual_information",
    "normalized_utilization_entropy",
    "utilization_entropy",
]

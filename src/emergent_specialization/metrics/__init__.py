"""Permutation-invariant diagnostics for behavioral differentiation."""

from .behavioral import behavioral_cosine_distance, competence_matrix, individual_accuracy
from .complementarity import complementarity_metrics
from .hse import hierarchic_social_entropy
from .information import mutual_information, normalized_utilization_entropy, utilization_entropy

__all__ = [
    "behavioral_cosine_distance",
    "competence_matrix",
    "individual_accuracy",
    "complementarity_metrics",
    "hierarchic_social_entropy",
    "mutual_information",
    "normalized_utilization_entropy",
    "utilization_entropy",
]

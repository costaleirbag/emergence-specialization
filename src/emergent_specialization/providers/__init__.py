"""Provider adapters. The experiment itself never depends on OMP details."""

from emergent_specialization.providers.base import LLMBackend
from emergent_specialization.providers.deepseek_direct import DeepSeekDirectBackend
from emergent_specialization.providers.mock import MockBackend
from emergent_specialization.providers.omp_rpc import OMPBackend

__all__ = ["LLMBackend", "MockBackend", "OMPBackend", "DeepSeekDirectBackend"]

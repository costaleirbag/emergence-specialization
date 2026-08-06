"""Provider adapters. The experiment itself never depends on OMP details."""

from .base import LLMBackend
from .mock import MockBackend
from .omp_rpc import OMPBackend

__all__ = ["LLMBackend", "MockBackend", "OMPBackend"]

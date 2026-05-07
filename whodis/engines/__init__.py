"""Detection engines for WhoDis."""

from whodis.engines.base import DetectionEngine, DetectionResult, ReferenceMatch
from whodis.engines.registry import EngineRegistry, register_default_engines
from whodis.engines.imagehash_engine import ImageHashEngine

__all__ = [
    "DetectionEngine",
    "DetectionResult",
    "ReferenceMatch",
    "EngineRegistry",
    "register_default_engines",
    "ImageHashEngine",
]

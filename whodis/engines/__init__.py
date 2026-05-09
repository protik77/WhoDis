"""Detection engines for WhoDis."""

from whodis.engines.base import DetectionEngine, DetectionResult, ReferenceMatch
from whodis.engines.imagehash_engine import ImageHashEngine
from whodis.engines.registry import EngineRegistry, register_default_engines

__all__ = [
    "DetectionEngine",
    "DetectionResult",
    "ReferenceMatch",
    "EngineRegistry",
    "register_default_engines",
    "ImageHashEngine",
]

# Conditionally export DeepFaceEngine if available
try:
    from whodis.engines.deepface_engine import DeepFaceEngine  # noqa: F401

    __all__.append("DeepFaceEngine")
except ImportError:
    pass

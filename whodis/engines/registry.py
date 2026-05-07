"""Registry for detection engines."""

from typing import Dict, Optional, Type

from whodis.config import DEFAULT_ENGINE
from whodis.engines.base import DetectionEngine


class EngineRegistry:
    """Registry for managing detection engines."""
    
    _engines: Dict[str, DetectionEngine] = {}
    _engine_classes: Dict[str, Type[DetectionEngine]] = {}
    
    @classmethod
    def register(cls, name: str, engine_class: Type[DetectionEngine]):
        """Register an engine class."""
        cls._engine_classes[name] = engine_class
    
    @classmethod
    def get_engine(cls, name: Optional[str] = None) -> Optional[DetectionEngine]:
        """
        Get an engine instance by name.
        
        If name is None, returns the default engine.
        Creates the instance on first request and caches it.
        """
        name = name or DEFAULT_ENGINE
        
        # Return cached instance if available
        if name in cls._engines:
            return cls._engines[name]
        
        # Create new instance
        engine_class = cls._engine_classes.get(name)
        if not engine_class:
            return None
        
        engine = engine_class()
        cls._engines[name] = engine
        return engine
    
    @classmethod
    def list_engines(cls) -> list:
        """List all registered engine names."""
        return list(cls._engine_classes.keys())
    
    @classmethod
    def clear_cache(cls):
        """Clear cached engine instances."""
        cls._engines.clear()


def register_default_engines():
    """Register the default engines."""
    from whodis.engines.imagehash_engine import ImageHashEngine
    
    EngineRegistry.register("imagehash", ImageHashEngine)


# Auto-register on import
register_default_engines()

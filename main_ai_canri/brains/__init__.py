"""Central package for Canri brain discovery and new brain implementations."""

from .catalog import BRAIN_MODULES, load_brain_registry

__all__ = ["BRAIN_MODULES", "load_brain_registry"]


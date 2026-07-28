"""Compatibility import for Canri's optional local-model brain."""

from brains.local_llm import LocalLLMBrain, LocalModelError, brain

__all__ = ["LocalLLMBrain", "LocalModelError", "brain"]

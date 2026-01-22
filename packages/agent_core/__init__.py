"""Konko AI Conversational Agent - Core Package."""

from .llm_provider import LLMProvider, LLMProviderError, create_llm

__version__ = "0.1.0"

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "create_llm",
]

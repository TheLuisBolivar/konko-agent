"""Konko AI Conversational Agent - Core Package."""

from .agent import AgentError, ConversationalAgent
from .escalation import EscalationEngine, EscalationResult
from .graph import GraphState, create_conversation_graph
from .llm_provider import LLMProvider, LLMProviderError, create_llm

__version__ = "0.1.0"

__all__ = [
    "AgentError",
    "ConversationalAgent",
    "EscalationEngine",
    "EscalationResult",
    "GraphState",
    "LLMProvider",
    "LLMProviderError",
    "create_conversation_graph",
    "create_llm",
]

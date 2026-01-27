"""LangGraph state machine for conversation flow control.

This module provides a state machine implementation using LangGraph
for better flow control, correction handling, and off-topic detection.
"""

from .builder import create_conversation_graph
from .state import GraphState

__all__ = ["create_conversation_graph", "GraphState"]

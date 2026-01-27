"""Escalation policies framework for Konko AI Agent.

This module provides the escalation engine and policy handlers for
detecting when conversations should be escalated to human agents.
"""

from .base import PolicyHandler
from .engine import EscalationEngine
from .result import EscalationResult

__all__ = [
    "EscalationEngine",
    "EscalationResult",
    "PolicyHandler",
]

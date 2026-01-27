"""Base class for escalation policy handlers.

This module defines the abstract base class that all policy handlers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from agent_runtime import ConversationState

from .result import EscalationResult


class PolicyHandler(ABC):
    """Abstract base class for escalation policy handlers.

    All policy handlers must inherit from this class and implement
    the evaluate method to check if escalation should occur.
    """

    policy_type: str = "base"

    @abstractmethod
    async def evaluate(
        self,
        state: ConversationState,
        user_message: str,
        config: Dict[str, Any],
        policy_id: str,
        reason: str,
    ) -> Optional[EscalationResult]:
        """Evaluate if escalation should occur based on the policy.

        Args:
            state: Current conversation state
            user_message: The latest user message
            config: Policy-specific configuration dictionary
            policy_id: Unique identifier for this policy instance
            reason: Human-readable reason configured for this policy

        Returns:
            EscalationResult if escalation should occur, None otherwise
        """
        pass

"""Timeout-based escalation policy handler.

This handler checks if the conversation has exceeded a configured
duration threshold and should be escalated to a human agent.
"""

from typing import Any, Dict, Optional

from agent_runtime import ConversationState

from ..base import PolicyHandler
from ..result import EscalationResult


class TimeoutPolicyHandler(PolicyHandler):
    """Handler for timeout-based escalation policies.

    Checks if the conversation duration has exceeded the configured maximum.

    Config options:
        max_duration_seconds: Maximum allowed conversation duration in seconds
    """

    policy_type: str = "timeout"

    async def evaluate(
        self,
        state: ConversationState,
        user_message: str,
        config: Dict[str, Any],
        policy_id: str,
        reason: str,
    ) -> Optional[EscalationResult]:
        """Check if conversation has exceeded timeout threshold.

        Args:
            state: Current conversation state
            user_message: The latest user message (not used for timeout)
            config: Policy configuration with 'max_duration_seconds'
            policy_id: Policy identifier
            reason: Configured escalation reason

        Returns:
            EscalationResult if timeout exceeded, None otherwise
        """
        max_duration = config.get("max_duration_seconds")

        if max_duration is None:
            return None

        try:
            max_duration = float(max_duration)
        except (TypeError, ValueError):
            return None

        current_duration = state.get_duration_seconds()

        if current_duration > max_duration:
            return EscalationResult(
                should_escalate=True,
                policy_id=policy_id,
                policy_type=self.policy_type,
                reason=reason,
                confidence=1.0,
                metadata={
                    "current_duration_seconds": current_duration,
                    "max_duration_seconds": max_duration,
                },
            )

        return None

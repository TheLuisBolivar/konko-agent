"""Completion-based escalation policy handler.

This handler checks if all required fields have been collected and
triggers escalation when the conversation is complete.
"""

from typing import Any, Dict, List, Optional

from agent_runtime import ConversationState

from ..base import PolicyHandler
from ..result import EscalationResult


class CompletionPolicyHandler(PolicyHandler):
    """Handler for completion-based escalation policies.

    Checks if all configured required fields have been collected.
    This can be used to escalate to a human once all info is gathered.

    Config options:
        required_fields: List of field names that must be collected
        escalate_when_complete: If True, escalate when all fields collected
                               If False, escalate when fields are missing (default: True)
    """

    policy_type: str = "completion"

    async def evaluate(
        self,
        state: ConversationState,
        user_message: str,
        config: Dict[str, Any],
        policy_id: str,
        reason: str,
    ) -> Optional[EscalationResult]:
        """Check if required fields completion status triggers escalation.

        Args:
            state: Current conversation state
            user_message: The latest user message (not used for completion check)
            config: Policy configuration with 'required_fields' list
            policy_id: Policy identifier
            reason: Configured escalation reason

        Returns:
            EscalationResult if completion condition met, None otherwise
        """
        required_fields: List[str] = config.get("required_fields", [])
        escalate_when_complete: bool = config.get("escalate_when_complete", True)

        if not required_fields:
            return None

        collected_data = state.get_collected_data()
        collected_field_names = set(collected_data.keys())
        required_field_names = set(required_fields)

        all_collected = required_field_names.issubset(collected_field_names)
        missing_fields = list(required_field_names - collected_field_names)

        if escalate_when_complete and all_collected:
            return EscalationResult(
                should_escalate=True,
                policy_id=policy_id,
                policy_type=self.policy_type,
                reason=reason,
                confidence=1.0,
                metadata={
                    "collected_fields": list(collected_field_names),
                    "required_fields": required_fields,
                },
            )
        elif not escalate_when_complete and not all_collected:
            return EscalationResult(
                should_escalate=True,
                policy_id=policy_id,
                policy_type=self.policy_type,
                reason=reason,
                confidence=1.0,
                metadata={
                    "missing_fields": missing_fields,
                    "collected_fields": list(collected_field_names),
                    "required_fields": required_fields,
                },
            )

        return None

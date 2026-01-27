"""Keyword-based escalation policy handler.

This handler checks if the user message contains any configured keywords
that should trigger an escalation to a human agent.
"""

from typing import Any, Dict, List, Optional

from agent_runtime import ConversationState

from ..base import PolicyHandler
from ..result import EscalationResult


class KeywordPolicyHandler(PolicyHandler):
    """Handler for keyword-based escalation policies.

    Checks if the user message contains any of the configured keywords.
    Matching is case-insensitive by default.

    Config options:
        keywords: List of keywords to check for
        case_sensitive: Whether matching is case-sensitive (default: False)
        match_whole_word: Whether to match whole words only (default: False)
    """

    policy_type: str = "keyword"

    async def evaluate(
        self,
        state: ConversationState,
        user_message: str,
        config: Dict[str, Any],
        policy_id: str,
        reason: str,
    ) -> Optional[EscalationResult]:
        """Check if user message contains any escalation keywords.

        Args:
            state: Current conversation state
            user_message: The latest user message
            config: Policy configuration with 'keywords' list
            policy_id: Policy identifier
            reason: Configured escalation reason

        Returns:
            EscalationResult if keyword found, None otherwise
        """
        keywords: List[str] = config.get("keywords", [])
        case_sensitive: bool = config.get("case_sensitive", False)
        match_whole_word: bool = config.get("match_whole_word", False)

        if not keywords:
            return None

        message_to_check = user_message if case_sensitive else user_message.lower()

        for keyword in keywords:
            keyword_to_match = keyword if case_sensitive else keyword.lower()

            if match_whole_word:
                # Split message into words and check for exact match
                words = message_to_check.split()
                if keyword_to_match in words:
                    return EscalationResult(
                        should_escalate=True,
                        policy_id=policy_id,
                        policy_type=self.policy_type,
                        reason=reason,
                        confidence=1.0,
                        metadata={"matched_keyword": keyword},
                    )
            else:
                if keyword_to_match in message_to_check:
                    return EscalationResult(
                        should_escalate=True,
                        policy_id=policy_id,
                        policy_type=self.policy_type,
                        reason=reason,
                        confidence=1.0,
                        metadata={"matched_keyword": keyword},
                    )

        return None

"""Sentiment-based escalation policy handler.

This handler uses an LLM to analyze the sentiment of user messages
and triggers escalation when negative sentiment is detected.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from agent_runtime import ConversationState

from ..base import PolicyHandler
from ..result import EscalationResult

if TYPE_CHECKING:
    from agent_core.llm_provider import LLMProvider


class SentimentPolicyHandler(PolicyHandler):
    """Handler for sentiment-based escalation policies.

    Uses an LLM to analyze the sentiment of user messages and
    triggers escalation when negative sentiment exceeds a threshold.

    Config options:
        threshold: Minimum negative sentiment score to trigger (default: 0.7)
        include_history: Whether to include conversation history (default: False)
    """

    policy_type: str = "sentiment"

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        """Initialize sentiment handler with optional LLM provider.

        Args:
            llm_provider: LLM provider for sentiment analysis
        """
        self.llm_provider = llm_provider

    async def evaluate(
        self,
        state: ConversationState,
        user_message: str,
        config: Dict[str, Any],
        policy_id: str,
        reason: str,
    ) -> Optional[EscalationResult]:
        """Analyze sentiment and check if escalation is needed.

        Args:
            state: Current conversation state
            user_message: The latest user message
            config: Policy configuration with 'threshold'
            policy_id: Policy identifier
            reason: Configured escalation reason

        Returns:
            EscalationResult if negative sentiment detected, None otherwise
        """
        if self.llm_provider is None:
            return None

        threshold: float = config.get("threshold", 0.7)
        include_history: bool = config.get("include_history", False)

        # Build the sentiment analysis prompt
        prompt = self._build_sentiment_prompt(state, user_message, include_history)

        try:
            response = await self.llm_provider.ainvoke(prompt)
            sentiment_score = self._parse_sentiment_response(response)

            if sentiment_score is not None and sentiment_score >= threshold:
                return EscalationResult(
                    should_escalate=True,
                    policy_id=policy_id,
                    policy_type=self.policy_type,
                    reason=reason,
                    confidence=sentiment_score,
                    metadata={
                        "sentiment_score": sentiment_score,
                        "threshold": threshold,
                        "analyzed_message": user_message,
                    },
                )
        except Exception:
            # If LLM call fails, don't trigger escalation
            pass

        return None

    def _build_sentiment_prompt(
        self,
        state: ConversationState,
        user_message: str,
        include_history: bool,
    ) -> str:
        """Build the prompt for sentiment analysis.

        Args:
            state: Current conversation state
            user_message: The latest user message
            include_history: Whether to include conversation history

        Returns:
            Formatted prompt string
        """
        context = ""
        if include_history and state.messages:
            recent_messages = state.messages[-5:]
            history_lines = []
            for msg in recent_messages:
                role = "User" if msg.role.value == "user" else "Agent"
                history_lines.append(f"{role}: {msg.content}")
            context = "Conversation context:\n" + "\n".join(history_lines) + "\n\n"

        return f"""{context}Analyze the sentiment of this message and rate the level of \
frustration, anger, or negative emotion on a scale from 0.0 to 1.0.

Message: "{user_message}"

Instructions:
- 0.0 = Very positive or neutral sentiment
- 0.5 = Mildly negative or slightly frustrated
- 1.0 = Very negative, angry, or extremely frustrated

Respond with ONLY a decimal number between 0.0 and 1.0, nothing else.

Sentiment score:"""

    def _parse_sentiment_response(self, response: str) -> Optional[float]:
        """Parse the LLM response to extract sentiment score.

        Args:
            response: LLM response string

        Returns:
            Sentiment score as float, or None if parsing fails
        """
        try:
            # Clean the response and extract the number
            cleaned = response.strip()
            score = float(cleaned)
            # Clamp to valid range
            return max(0.0, min(1.0, score))
        except (ValueError, TypeError):
            return None

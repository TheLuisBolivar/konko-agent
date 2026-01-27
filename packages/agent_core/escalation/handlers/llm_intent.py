"""LLM intent-based escalation policy handler.

This handler uses an LLM to detect specific intents in user messages
that indicate the conversation should be escalated.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent_runtime import ConversationState

from ..base import PolicyHandler
from ..result import EscalationResult

if TYPE_CHECKING:
    from agent_core.llm_provider import LLMProvider


class LLMIntentPolicyHandler(PolicyHandler):
    """Handler for LLM intent-based escalation policies.

    Uses an LLM to detect specific intents that should trigger
    escalation to a human agent.

    Config options:
        intents: List of intent descriptions to detect
        confidence_threshold: Minimum confidence for detection (default: 0.8)
    """

    policy_type: str = "llm_intent"

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        """Initialize intent handler with optional LLM provider.

        Args:
            llm_provider: LLM provider for intent detection
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
        """Detect escalation intents in user message.

        Args:
            state: Current conversation state
            user_message: The latest user message
            config: Policy configuration with 'intents' list
            policy_id: Policy identifier
            reason: Configured escalation reason

        Returns:
            EscalationResult if escalation intent detected, None otherwise
        """
        if self.llm_provider is None:
            return None

        intents: List[str] = config.get("intents", [])
        confidence_threshold: float = config.get("confidence_threshold", 0.8)

        if not intents:
            # Default escalation intents if none configured
            intents = [
                "user wants to speak with a human",
                "user is requesting a human agent",
                "user wants to escalate the conversation",
                "user is expressing extreme frustration",
                "user is threatening to leave or cancel",
            ]

        prompt = self._build_intent_prompt(user_message, intents)

        try:
            response = await self.llm_provider.ainvoke(prompt)
            detected_intent, confidence = self._parse_intent_response(response)

            if detected_intent and confidence >= confidence_threshold:
                return EscalationResult(
                    should_escalate=True,
                    policy_id=policy_id,
                    policy_type=self.policy_type,
                    reason=reason,
                    confidence=confidence,
                    metadata={
                        "detected_intent": detected_intent,
                        "confidence": confidence,
                        "analyzed_message": user_message,
                        "configured_intents": intents,
                    },
                )
        except Exception:
            # If LLM call fails, don't trigger escalation
            pass

        return None

    def _build_intent_prompt(
        self,
        user_message: str,
        intents: List[str],
    ) -> str:
        """Build the prompt for intent detection.

        Args:
            user_message: The latest user message
            intents: List of intent descriptions to detect

        Returns:
            Formatted prompt string
        """
        intents_list = "\n".join(f"- {intent}" for intent in intents)

        return f"""Analyze the following user message and determine if it matches \
any of these escalation intents:

{intents_list}

User message: "{user_message}"

Instructions:
1. If the message matches one of the intents, respond with:
   DETECTED: [intent description]
   CONFIDENCE: [0.0-1.0]

2. If no intent is detected, respond with:
   DETECTED: NONE
   CONFIDENCE: 0.0

Only respond with the format above, nothing else.

Response:"""

    def _parse_intent_response(self, response: str) -> tuple[Optional[str], float]:
        """Parse the LLM response to extract intent and confidence.

        Args:
            response: LLM response string

        Returns:
            Tuple of (detected_intent, confidence)
        """
        detected_intent: Optional[str] = None
        confidence: float = 0.0

        try:
            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("DETECTED:"):
                    intent = line.replace("DETECTED:", "").strip()
                    if intent.upper() != "NONE":
                        detected_intent = intent
                elif line.startswith("CONFIDENCE:"):
                    conf_str = line.replace("CONFIDENCE:", "").strip()
                    confidence = float(conf_str)
                    confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            pass

        return detected_intent, confidence

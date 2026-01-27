"""Escalation engine for orchestrating policy evaluation.

This module provides the main engine that manages escalation policy handlers
and evaluates them in priority order.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Type

from agent_config import AgentConfig, EscalationPolicy
from agent_runtime import ConversationState

from .base import PolicyHandler
from .handlers import (
    CompletionPolicyHandler,
    KeywordPolicyHandler,
    LLMIntentPolicyHandler,
    SentimentPolicyHandler,
    TimeoutPolicyHandler,
)
from .result import EscalationResult

if TYPE_CHECKING:
    from agent_core.llm_provider import LLMProvider


class EscalationEngine:
    """Engine for evaluating escalation policies.

    Manages policy handlers and evaluates them in priority order:
    1. keyword - Fastest, simple string matching
    2. timeout - Fast, simple duration check
    3. sentiment - Requires LLM call
    4. llm_intent - Requires LLM call
    5. completion - Fast, checks field collection status

    The engine stops at the first handler that triggers escalation.
    """

    # Priority order for policy evaluation (lower = higher priority)
    POLICY_PRIORITY: Dict[str, int] = {
        "keyword": 1,
        "timeout": 2,
        "sentiment": 3,
        "llm_intent": 4,
        "completion": 5,
    }

    # Mapping of policy types to handler classes
    HANDLER_CLASSES: Dict[str, Type[PolicyHandler]] = {
        "keyword": KeywordPolicyHandler,
        "timeout": TimeoutPolicyHandler,
        "sentiment": SentimentPolicyHandler,
        "llm_intent": LLMIntentPolicyHandler,
        "completion": CompletionPolicyHandler,
    }

    def __init__(
        self,
        config: AgentConfig,
        llm_provider: Optional["LLMProvider"] = None,
    ):
        """Initialize the escalation engine.

        Args:
            config: Agent configuration containing escalation policies
            llm_provider: Optional LLM provider for sentiment/intent handlers
        """
        self.config = config
        self.llm_provider = llm_provider
        self._handlers: Dict[str, PolicyHandler] = {}
        self._initialize_handlers()

    def _initialize_handlers(self) -> None:
        """Initialize handlers for each configured policy type."""
        for handler_type, handler_class in self.HANDLER_CLASSES.items():
            # Handlers that need LLM provider
            if handler_type in ("sentiment", "llm_intent"):
                handler = handler_class(self.llm_provider)  # type: ignore[call-arg]
                self._handlers[handler_type] = handler
            else:
                self._handlers[handler_type] = handler_class()

    def _get_sorted_policies(self) -> List[tuple[EscalationPolicy, int]]:
        """Get enabled policies sorted by priority.

        Returns:
            List of (policy, index) tuples sorted by priority
        """
        enabled_policies = [
            (policy, idx)
            for idx, policy in enumerate(self.config.escalation_policies)
            if policy.enabled
        ]

        # Sort by priority (policy type priority)
        enabled_policies.sort(key=lambda x: self.POLICY_PRIORITY.get(x[0].policy_type, 999))

        return enabled_policies

    async def evaluate(
        self,
        state: ConversationState,
        user_message: str,
    ) -> Optional[EscalationResult]:
        """Evaluate all enabled policies and return first escalation result.

        Policies are evaluated in priority order. Evaluation stops when
        the first policy triggers escalation.

        Args:
            state: Current conversation state
            user_message: The latest user message

        Returns:
            EscalationResult if escalation triggered, None otherwise
        """
        sorted_policies = self._get_sorted_policies()

        for policy, idx in sorted_policies:
            handler = self._handlers.get(policy.policy_type)
            if handler is None:
                continue

            policy_id = f"policy_{idx}_{policy.policy_type}"

            result = await handler.evaluate(
                state=state,
                user_message=user_message,
                config=policy.config,
                policy_id=policy_id,
                reason=policy.reason,
            )

            if result is not None and result.should_escalate:
                return result

        return None

    async def evaluate_all(
        self,
        state: ConversationState,
        user_message: str,
    ) -> List[EscalationResult]:
        """Evaluate all enabled policies and return all escalation results.

        Unlike evaluate(), this method doesn't stop at the first match
        and returns all policies that would trigger escalation.

        Args:
            state: Current conversation state
            user_message: The latest user message

        Returns:
            List of all EscalationResults that triggered
        """
        results: List[EscalationResult] = []
        sorted_policies = self._get_sorted_policies()

        for policy, idx in sorted_policies:
            handler = self._handlers.get(policy.policy_type)
            if handler is None:
                continue

            policy_id = f"policy_{idx}_{policy.policy_type}"

            result = await handler.evaluate(
                state=state,
                user_message=user_message,
                config=policy.config,
                policy_id=policy_id,
                reason=policy.reason,
            )

            if result is not None and result.should_escalate:
                results.append(result)

        return results

    def has_policies(self) -> bool:
        """Check if any escalation policies are configured and enabled.

        Returns:
            True if at least one enabled policy exists
        """
        return any(p.enabled for p in self.config.escalation_policies)

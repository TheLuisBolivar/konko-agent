"""Escalation result model.

This module defines the data structure returned when an escalation policy
determines that a conversation should be escalated.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EscalationResult:
    """Result of an escalation policy evaluation.

    Attributes:
        should_escalate: Whether escalation should occur
        policy_id: Identifier of the policy that triggered escalation
        policy_type: Type of the policy (keyword, timeout, sentiment, etc.)
        reason: Human-readable reason for the escalation
        confidence: Confidence score for the escalation decision (0.0-1.0)
        metadata: Additional metadata about the escalation
    """

    should_escalate: bool
    policy_id: str
    policy_type: str
    reason: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate escalation result attributes."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.metadata is None:
            self.metadata = {}

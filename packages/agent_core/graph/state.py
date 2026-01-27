"""Graph state definition for LangGraph conversation flow.

This module defines the TypedDict state that flows through the graph nodes,
carrying conversation context and flow control information.
"""

from typing import Any, Optional, TypedDict

from agent_runtime import ConversationState


class GraphState(TypedDict):
    """State that flows through the conversation graph.

    Attributes:
        conversation: The underlying conversation state with message history
        user_message: The current user message being processed
        next_action: The next action to take in the conversation flow
        should_escalate: Whether the conversation should be escalated
        escalation_reason: Reason for escalation if applicable
        is_correction: Whether the user is correcting a previously provided value
        correction_field: Field being corrected if is_correction is True
        is_off_topic: Whether the user's response is off-topic
        extracted_value: Value extracted from the user's message
        is_valid: Whether the extracted value passed validation
        current_field: Name of the field currently being collected
        response: The response to send to the user
        metadata: Additional metadata for the graph execution
    """

    conversation: ConversationState
    user_message: str
    next_action: str
    should_escalate: bool
    escalation_reason: Optional[str]
    is_correction: bool
    correction_field: Optional[str]
    is_off_topic: bool
    extracted_value: Optional[str]
    is_valid: bool
    current_field: Optional[str]
    response: str
    metadata: dict[str, Any]


def create_initial_state(
    conversation: ConversationState,
    user_message: str,
) -> GraphState:
    """Create an initial graph state from conversation state and user message.

    Args:
        conversation: The current conversation state
        user_message: The user's message to process

    Returns:
        Initialized GraphState with default values
    """
    return GraphState(
        conversation=conversation,
        user_message=user_message,
        next_action="",
        should_escalate=False,
        escalation_reason=None,
        is_correction=False,
        correction_field=None,
        is_off_topic=False,
        extracted_value=None,
        is_valid=False,
        current_field=None,
        response="",
        metadata={},
    )

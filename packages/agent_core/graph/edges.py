"""Edge routing functions for the LangGraph conversation flow.

This module provides the conditional routing functions that determine
the next node to execute based on the current graph state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .state import GraphState

if TYPE_CHECKING:
    from agent_core.agent import ConversationalAgent


def route_after_escalation_check(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["escalate", "check_correction"]:
    """Route after checking for escalation.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Next node to execute
    """
    if state["should_escalate"]:
        return "escalate"
    return "check_correction"


def route_after_correction_check(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["extract_field", "check_off_topic"]:
    """Route after checking for corrections.

    If user is correcting a value, go directly to extraction.
    Otherwise, check if the response is off-topic.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Next node to execute
    """
    if state["is_correction"]:
        return "extract_field"
    return "check_off_topic"


def route_after_off_topic_check(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["extract_field", "prompt_next", "complete"]:
    """Route after checking for off-topic responses.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Next node to execute
    """
    # Check if all fields are collected
    next_field = agent.get_next_field_to_collect(state["conversation"])

    if next_field is None:
        # All fields collected
        return "complete"

    if state["is_off_topic"]:
        # Off-topic: skip extraction, go directly to prompt
        return "prompt_next"

    # On-topic: try to extract the field value
    return "extract_field"


def route_after_validate(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["prompt_next", "complete"]:
    """Route after validation.

    If valid and more fields to collect, prompt for next.
    If valid and no more fields, complete.
    If invalid, re-prompt for current field.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Next node to execute
    """
    # Check if there are more fields to collect
    next_field = agent.get_next_field_to_collect(state["conversation"])

    if next_field is None:
        # All fields collected
        return "complete"

    # More fields needed (or current field invalid, will re-prompt)
    return "prompt_next"


def should_continue_after_prompt(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["__end__"]:
    """Determine if we should continue after prompting.

    After generating a prompt response, we always end and wait
    for the next user message.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Always returns END to wait for next user input
    """
    return "__end__"


def should_continue_after_escalate(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["__end__"]:
    """Determine if we should continue after escalation.

    After escalation, we always end the graph execution.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Always returns END
    """
    return "__end__"


def should_continue_after_complete(
    state: GraphState,
    agent: ConversationalAgent,
) -> Literal["__end__"]:
    """Determine if we should continue after completion.

    After completion, we always end the graph execution.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Always returns END
    """
    return "__end__"

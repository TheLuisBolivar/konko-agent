"""Node functions for the LangGraph conversation flow.

This module provides the individual node functions that perform specific
actions in the conversation graph (escalation checking, field extraction,
validation, etc.).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .state import GraphState

if TYPE_CHECKING:
    from agent_core.agent import ConversationalAgent


# Correction detection patterns
CORRECTION_PATTERNS = [
    r"(?:no|nope|actually|sorry|wait),?\s*(?:my|the|it'?s?)\s+(\w+)\s+(?:is|should be|was)",
    r"(?:i meant|i mean|that'?s? wrong|correction:?)\s+(?:my|the)?\s*(\w+)?",
    r"(?:let me correct|please change|update)\s+(?:my|the)?\s*(\w+)?",
    r"(?:that'?s? not right|wrong)\s*[,.]?\s*(?:my|the|it'?s?)?\s*(\w+)?",
]

# Off-topic detection patterns (common off-topic responses)
OFF_TOPIC_PATTERNS = [
    r"^(?:hi|hello|hey|what'?s? up|how are you|good morning|good afternoon|good evening)\s*[!.?]?$",
    r"^(?:what|who|why|how|when|where)\s+(?:are you|is this|do you|can you|did)",
    r"^(?:tell me (?:a joke|about|more)|what'?s? the weather|help me with something else)",
    r"^(?:i have a question|can i ask|quick question|unrelated but)",
]


async def check_escalation_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Check if the conversation should be escalated to a human agent.

    Uses the existing EscalationEngine to evaluate all configured policies.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with escalation information
    """
    if not agent.escalation_engine.has_policies():
        state["should_escalate"] = False
        state["escalation_reason"] = None
        return state

    result = await agent.escalation_engine.evaluate(
        state["conversation"],
        state["user_message"],
    )

    if result and result.should_escalate:
        state["should_escalate"] = True
        state["escalation_reason"] = result.reason
        state["metadata"]["escalation_policy_id"] = result.policy_id
        state["metadata"]["escalation_confidence"] = result.confidence
    else:
        state["should_escalate"] = False
        state["escalation_reason"] = None

    return state


async def check_correction_node(  # noqa: C901
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Detect if the user is correcting a previously provided value.

    Detects patterns like:
    - "No, my email is..."
    - "Actually, it should be..."
    - "Let me correct that..."

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with correction information
    """
    user_message = state["user_message"].lower().strip()
    collected_fields = set(state["conversation"].get_collected_data().keys())

    # Check for correction patterns
    for pattern in CORRECTION_PATTERNS:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            # Try to identify which field is being corrected
            field_hint = match.group(1) if match.groups() else None

            if field_hint:
                # Check if field_hint matches any collected field
                for field_name in collected_fields:
                    if field_hint.lower() in field_name.lower():
                        state["is_correction"] = True
                        state["correction_field"] = field_name
                        return state

            # If no specific field identified but correction intent detected,
            # mark as correction and let extraction determine the field
            if collected_fields:
                state["is_correction"] = True
                state["correction_field"] = None  # Will be determined during extraction
                return state

    # Use LLM for ambiguous cases if the message suggests correction intent
    correction_keywords = ["no,", "actually", "sorry", "wrong", "correct", "meant"]
    if any(keyword in user_message for keyword in correction_keywords) and collected_fields:
        # Use LLM to determine if this is a correction
        prompt = f"""Determine if the user is correcting a previously provided value.

User message: "{state['user_message']}"

Previously collected fields: {list(collected_fields)}

Respond with ONLY one of:
- CORRECTION:<field_name> if correcting a specific field
- CORRECTION:UNKNOWN if correcting but field unclear
- NOT_CORRECTION if not a correction

Response:"""

        try:
            llm_response = await agent.llm_provider.ainvoke(prompt)
            llm_response = llm_response.strip().upper()

            if llm_response.startswith("CORRECTION:"):
                field_part = llm_response.split(":", 1)[1].strip()
                state["is_correction"] = True
                state["correction_field"] = field_part if field_part != "UNKNOWN" else None
                return state
        except Exception:
            # If LLM fails, fall through to no correction
            pass

    state["is_correction"] = False
    state["correction_field"] = None
    return state


async def check_off_topic_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Detect if the user's response is off-topic or irrelevant.

    Detects when users go off-topic from the data collection task.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with off-topic information
    """
    user_message = state["user_message"].strip()

    # Check for common off-topic patterns
    for pattern in OFF_TOPIC_PATTERNS:
        if re.match(pattern, user_message, re.IGNORECASE):
            state["is_off_topic"] = True
            return state

    # For more nuanced detection, use LLM
    next_field = agent.get_next_field_to_collect(state["conversation"])
    if next_field:
        prompt = f"""Determine if the user's response is relevant to the question being asked.

We are collecting: {next_field.name} ({next_field.field_type})
User's response: "{state['user_message']}"

A response is OFF-TOPIC if it:
- Asks unrelated questions
- Changes the subject entirely
- Doesn't attempt to provide the requested information

A response is ON-TOPIC if it:
- Attempts to provide the requested information (even if incomplete/invalid)
- Asks for clarification about the question
- Requests to skip or decline

Respond with ONLY: ON_TOPIC or OFF_TOPIC

Response:"""

        try:
            llm_response = await agent.llm_provider.ainvoke(prompt)
            is_off_topic = "OFF_TOPIC" in llm_response.strip().upper()
            state["is_off_topic"] = is_off_topic
            return state
        except Exception:
            # If LLM fails, assume on-topic
            pass

    state["is_off_topic"] = False
    return state


async def extract_field_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Extract field value from the user's message.

    Reuses the agent's _build_extraction_prompt() method.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with extracted value
    """
    # Determine which field to extract
    if state["is_correction"] and state["correction_field"]:
        # For corrections, find the field config by name
        field = None
        for f in agent.config.fields:
            if f.name == state["correction_field"]:
                field = f
                break
        if not field:
            # Field not found, get next field instead
            field = agent.get_next_field_to_collect(state["conversation"])
    else:
        field = agent.get_next_field_to_collect(state["conversation"])

    if not field:
        state["extracted_value"] = None
        state["current_field"] = None
        return state

    state["current_field"] = field.name

    # Build extraction prompt and invoke LLM
    extraction_prompt = agent._build_extraction_prompt(
        field, state["user_message"], state["conversation"]
    )

    try:
        extracted_value = await agent.llm_provider.ainvoke(extraction_prompt)
        extracted_value = extracted_value.strip()

        if extracted_value in ("NOT_PROVIDED", "INVALID"):
            state["extracted_value"] = None
        else:
            state["extracted_value"] = extracted_value
    except Exception:
        state["extracted_value"] = None

    return state


async def validate_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Validate the extracted field value.

    Reuses the agent's _validate_field_value() method.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with validation result
    """
    if not state["extracted_value"] or not state["current_field"]:
        state["is_valid"] = False
        return state

    # Find the field config
    field = None
    for f in agent.config.fields:
        if f.name == state["current_field"]:
            field = f
            break

    if not field:
        state["is_valid"] = False
        return state

    # Validate using agent's method
    is_valid = agent._validate_field_value(field, state["extracted_value"])
    state["is_valid"] = is_valid

    # If valid, update the conversation state
    if is_valid:
        state["conversation"].update_field_value(
            state["current_field"],
            state["extracted_value"],
            True,
        )

    return state


async def prompt_next_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Generate a prompt asking for the next field or re-asking current field.

    Reuses the agent's _build_field_prompt() method.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with response
    """
    next_field = agent.get_next_field_to_collect(state["conversation"])

    if not next_field:
        # No more fields - this shouldn't happen if routing is correct
        state["response"] = "Thank you for providing all the information."
        return state

    # Handle off-topic responses with a gentle redirect
    if state["is_off_topic"]:
        redirect_prompt = f"""{agent._build_system_prompt()}

The user went off-topic. Gently redirect them back to the conversation.

User's off-topic message: "{state['user_message']}"
We need to collect: {next_field.name} ({next_field.field_type})

Generate a brief, friendly response that:
1. Briefly acknowledges their message (don't be dismissive)
2. Gently redirects them to provide the {next_field.name}

Keep it short and conversational."""

        try:
            response = await agent.llm_provider.ainvoke(redirect_prompt)
            state["response"] = response.strip()
            return state
        except Exception:
            # Fallback response
            field_name = next_field.name
            state["response"] = f"I appreciate that! Could you please provide your {field_name}?"
            return state

    # Handle invalid input with helpful feedback
    if state["extracted_value"] is None and state["user_message"]:
        invalid_prompt = f"""{agent._build_system_prompt()}

The user's response didn't contain a valid {next_field.name}.

User's message: "{state['user_message']}"
Field needed: {next_field.name} (type: {next_field.field_type})

Generate a brief, helpful response that:
1. Explains what format is expected
2. Asks them to try again

Keep it friendly and concise."""

        try:
            response = await agent.llm_provider.ainvoke(invalid_prompt)
            state["response"] = response.strip()
            return state
        except Exception:
            pass

    # Standard field prompt
    field_prompt = agent._build_field_prompt(next_field, state["conversation"])

    try:
        response = await agent.llm_provider.ainvoke(field_prompt)
        state["response"] = response.strip()
    except Exception as e:
        state["response"] = f"Could you please provide your {next_field.name}?"
        state["metadata"]["prompt_error"] = str(e)

    return state


async def escalate_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Handle escalation by marking state and generating response.

    Reuses the escalation logic from agent._handle_escalation().

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with escalation response
    """
    # Mark the conversation as escalated
    policy_id = state["metadata"].get("escalation_policy_id")
    reason = state["escalation_reason"] or "User requested human agent"

    state["conversation"].mark_escalated(reason, policy_id)

    # Generate escalation message
    state["response"] = (
        "I understand you'd like to speak with a human agent. "
        "I'm connecting you now. Thank you for your patience."
    )

    return state


async def complete_node(
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Generate completion message when all fields are collected.

    Args:
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state with completion response
    """
    collected_data = state["conversation"].get_collected_data()

    completion_prompt = f"""{agent._build_system_prompt()}

All required information has been collected:
{collected_data}

Generate a brief, friendly thank you message confirming the information was received.
Keep it short (1-2 sentences)."""

    try:
        response = await agent.llm_provider.ainvoke(completion_prompt)
        state["response"] = response.strip()
    except Exception:
        state["response"] = "Thank you! We have all the information we need."

    # Mark conversation as completed
    state["conversation"].mark_completed()

    return state

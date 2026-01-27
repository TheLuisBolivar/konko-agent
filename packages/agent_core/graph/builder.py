"""Graph builder for the LangGraph conversation flow.

This module provides the function to construct and compile the
conversation state machine graph.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]

from .edges import (
    route_after_correction_check,
    route_after_escalation_check,
    route_after_off_topic_check,
    route_after_validate,
)
from .nodes import (
    check_correction_node,
    check_escalation_node,
    check_off_topic_node,
    complete_node,
    escalate_node,
    extract_field_node,
    prompt_next_node,
    validate_node,
)
from .state import GraphState

if TYPE_CHECKING:
    from agent_core.agent import ConversationalAgent
    from langgraph.graph.state import CompiledStateGraph  # type: ignore[import-not-found]


def create_conversation_graph(agent: ConversationalAgent) -> CompiledStateGraph:
    """Create and compile the conversation state machine graph.

    The graph follows this flow:
    ```
    START → check_escalation
               │
        ┌──────┴──────┐
        ↓             ↓
    escalate    check_correction
        ↓             │
       END     ┌──────┴──────┐
               ↓             ↓
        extract_field   check_off_topic
               │             │
               ↓      ┌──────┴──────┐
            validate  ↓             ↓
               │   prompt_next   complete
        ┌──────┴──────┐   │         ↓
        ↓             ↓   ↓        END
    prompt_next   complete
        ↓             ↓
       END           END
    ```

    Args:
        agent: The conversational agent instance to bind to node functions

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the workflow graph
    workflow: StateGraph[GraphState, Any, Any] = StateGraph(GraphState)

    # Add nodes with agent bound via partial
    workflow.add_node(
        "check_escalation",
        partial(_wrap_node, check_escalation_node, agent=agent),
    )
    workflow.add_node(
        "check_correction",
        partial(_wrap_node, check_correction_node, agent=agent),
    )
    workflow.add_node(
        "check_off_topic",
        partial(_wrap_node, check_off_topic_node, agent=agent),
    )
    workflow.add_node(
        "extract_field",
        partial(_wrap_node, extract_field_node, agent=agent),
    )
    workflow.add_node(
        "validate",
        partial(_wrap_node, validate_node, agent=agent),
    )
    workflow.add_node(
        "prompt_next",
        partial(_wrap_node, prompt_next_node, agent=agent),
    )
    workflow.add_node(
        "escalate",
        partial(_wrap_node, escalate_node, agent=agent),
    )
    workflow.add_node(
        "complete",
        partial(_wrap_node, complete_node, agent=agent),
    )

    # Set entry point
    workflow.set_entry_point("check_escalation")

    # Add conditional edges from check_escalation
    workflow.add_conditional_edges(
        "check_escalation",
        partial(route_after_escalation_check, agent=agent),
        {
            "escalate": "escalate",
            "check_correction": "check_correction",
        },
    )

    # Add conditional edges from check_correction
    workflow.add_conditional_edges(
        "check_correction",
        partial(route_after_correction_check, agent=agent),
        {
            "extract_field": "extract_field",
            "check_off_topic": "check_off_topic",
        },
    )

    # Add conditional edges from check_off_topic
    workflow.add_conditional_edges(
        "check_off_topic",
        partial(route_after_off_topic_check, agent=agent),
        {
            "extract_field": "extract_field",
            "prompt_next": "prompt_next",
            "complete": "complete",
        },
    )

    # Add edge from extract_field to validate
    workflow.add_edge("extract_field", "validate")

    # Add conditional edges from validate
    workflow.add_conditional_edges(
        "validate",
        partial(route_after_validate, agent=agent),
        {
            "prompt_next": "prompt_next",
            "complete": "complete",
        },
    )

    # Terminal nodes go to END
    workflow.add_edge("escalate", END)
    workflow.add_edge("prompt_next", END)
    workflow.add_edge("complete", END)

    # Compile and return
    return workflow.compile()


async def _wrap_node(
    node_func: Any,
    state: GraphState,
    agent: ConversationalAgent,
) -> GraphState:
    """Wrap and handle async node execution.

    Args:
        node_func: The node function to execute
        state: Current graph state
        agent: The conversational agent instance

    Returns:
        Updated graph state
    """
    return await node_func(state, agent)  # type: ignore[no-any-return]

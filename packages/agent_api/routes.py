"""API routes for conversation management."""

from fastapi import APIRouter, HTTPException  # type: ignore[import-not-found]

from agent_core import AgentError

from .app import get_app_state
from .models import (
    ConversationResponse,
    ErrorResponse,
    MessageRequest,
    MessageResponse,
    StartConversationResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post(
    "",
    response_model=StartConversationResponse,
    responses={503: {"model": ErrorResponse}},
)  # type: ignore[misc]
async def start_conversation() -> StartConversationResponse:
    """Start a new conversation.

    Returns:
        StartConversationResponse with session ID and greeting

    Raises:
        HTTPException: If agent is not configured
    """
    state = get_app_state()

    if state.agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agent not configured. Please configure the agent first.",
        )

    conversation_state = state.agent.start_conversation()

    return StartConversationResponse(
        session_id=conversation_state.session_id,
        greeting=conversation_state.messages[0].content,
        status=conversation_state.status.value,
    )


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)  # type: ignore[misc]
async def send_message(session_id: str, request: MessageRequest) -> MessageResponse:
    """Send a message to an existing conversation.

    Args:
        session_id: The conversation session ID
        request: The message request containing user content

    Returns:
        MessageResponse with agent's response

    Raises:
        HTTPException: If session not found or agent error
    """
    state = get_app_state()

    if state.agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agent not configured. Please configure the agent first.",
        )

    if state.store is None:
        raise HTTPException(status_code=503, detail="Store not initialized.")

    # Get existing conversation state
    conversation_state = state.store.get(session_id)
    if conversation_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation with session_id '{session_id}' not found.",
        )

    try:
        response, updated_state = await state.agent.process_message(
            conversation_state, request.content
        )

        return MessageResponse(
            response=response,
            session_id=updated_state.session_id,
            status=updated_state.status.value,
            collected_data=updated_state.get_collected_data(),
        )
    except AgentError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{session_id}",
    response_model=ConversationResponse,
    responses={404: {"model": ErrorResponse}},
)  # type: ignore[misc]
async def get_conversation(session_id: str) -> ConversationResponse:
    """Get the current state of a conversation.

    Args:
        session_id: The conversation session ID

    Returns:
        ConversationResponse with full conversation state

    Raises:
        HTTPException: If session not found
    """
    state = get_app_state()

    if state.store is None:
        raise HTTPException(status_code=503, detail="Store not initialized.")

    conversation_state = state.store.get(session_id)
    if conversation_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation with session_id '{session_id}' not found.",
        )

    return ConversationResponse(
        session_id=conversation_state.session_id,
        status=conversation_state.status.value,
        messages=[
            {"role": msg.role.value, "content": msg.content, "timestamp": msg.timestamp}
            for msg in conversation_state.messages
        ],
        collected_data=conversation_state.get_collected_data(),
        started_at=conversation_state.started_at,
        updated_at=conversation_state.updated_at,
    )


@router.delete(
    "/{session_id}",
    responses={404: {"model": ErrorResponse}},
)  # type: ignore[misc]
async def delete_conversation(session_id: str) -> dict[str, str]:
    """Delete a conversation.

    Args:
        session_id: The conversation session ID

    Returns:
        Confirmation message

    Raises:
        HTTPException: If session not found
    """
    state = get_app_state()

    if state.store is None:
        raise HTTPException(status_code=503, detail="Store not initialized.")

    # Check if conversation exists
    conversation_state = state.store.get(session_id)
    if conversation_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation with session_id '{session_id}' not found.",
        )

    # Delete the conversation
    state.store.delete(session_id)

    return {"message": f"Conversation '{session_id}' deleted successfully."}

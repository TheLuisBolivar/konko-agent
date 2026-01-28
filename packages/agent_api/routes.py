"""API routes for conversation management."""

import time

from agent_core import AgentError
from agent_core.metrics import (
    ACTIVE_CONVERSATIONS,
    CONVERSATIONS,
    HTTP_LATENCY,
    HTTP_REQUESTS,
    MESSAGES_PROCESSED,
)
from fastapi import APIRouter, HTTPException  # type: ignore[import-not-found]

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
    start_time = time.perf_counter()
    status_code = "200"

    try:
        state = get_app_state()

        if state.agent is None:
            status_code = "503"
            raise HTTPException(
                status_code=503,
                detail="Agent not configured. Please configure the agent first.",
            )

        conversation_state = state.agent.start_conversation()

        # Track metrics
        ACTIVE_CONVERSATIONS.inc()
        CONVERSATIONS.labels(status="started").inc()

        return StartConversationResponse(
            session_id=conversation_state.session_id,
            greeting=conversation_state.messages[0].content,
            status=conversation_state.status.value,
        )
    except HTTPException:
        raise
    except Exception:
        status_code = "500"
        raise
    finally:
        HTTP_LATENCY.labels(method="POST", endpoint="/conversations").observe(
            time.perf_counter() - start_time
        )
        HTTP_REQUESTS.labels(method="POST", endpoint="/conversations", status=status_code).inc()


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
    start_time = time.perf_counter()
    status_code = "200"

    try:
        state = get_app_state()

        if state.agent is None:
            status_code = "503"
            raise HTTPException(
                status_code=503,
                detail="Agent not configured. Please configure the agent first.",
            )

        if state.store is None:
            status_code = "503"
            raise HTTPException(status_code=503, detail="Store not initialized.")

        # Get existing conversation state
        conversation_state = state.store.get(session_id)
        if conversation_state is None:
            status_code = "404"
            raise HTTPException(
                status_code=404,
                detail=f"Conversation with session_id '{session_id}' not found.",
            )

        response, updated_state = await state.agent.process_message(
            conversation_state, request.content
        )

        MESSAGES_PROCESSED.labels(status="success").inc()

        return MessageResponse(
            response=response,
            session_id=updated_state.session_id,
            status=updated_state.status.value,
            collected_data=updated_state.get_collected_data(),
        )
    except AgentError as e:
        status_code = "500"
        MESSAGES_PROCESSED.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception:
        status_code = "500"
        MESSAGES_PROCESSED.labels(status="error").inc()
        raise
    finally:
        HTTP_LATENCY.labels(method="POST", endpoint="/messages").observe(
            time.perf_counter() - start_time
        )
        HTTP_REQUESTS.labels(method="POST", endpoint="/messages", status=status_code).inc()


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
    start_time = time.perf_counter()
    status_code = "200"

    try:
        state = get_app_state()

        if state.store is None:
            status_code = "503"
            raise HTTPException(status_code=503, detail="Store not initialized.")

        conversation_state = state.store.get(session_id)
        if conversation_state is None:
            status_code = "404"
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
    except HTTPException:
        raise
    except Exception:
        status_code = "500"
        raise
    finally:
        HTTP_LATENCY.labels(method="GET", endpoint="/conversations/{id}").observe(
            time.perf_counter() - start_time
        )
        HTTP_REQUESTS.labels(method="GET", endpoint="/conversations/{id}", status=status_code).inc()


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
    start_time = time.perf_counter()
    status_code = "200"

    try:
        state = get_app_state()

        if state.store is None:
            status_code = "503"
            raise HTTPException(status_code=503, detail="Store not initialized.")

        # Check if conversation exists
        conversation_state = state.store.get(session_id)
        if conversation_state is None:
            status_code = "404"
            raise HTTPException(
                status_code=404,
                detail=f"Conversation with session_id '{session_id}' not found.",
            )

        # Delete the conversation
        state.store.delete(session_id)

        # Track metrics
        ACTIVE_CONVERSATIONS.dec()
        CONVERSATIONS.labels(status="deleted").inc()

        return {"message": f"Conversation '{session_id}' deleted successfully."}
    except HTTPException:
        raise
    except Exception:
        status_code = "500"
        raise
    finally:
        HTTP_LATENCY.labels(method="DELETE", endpoint="/conversations/{id}").observe(
            time.perf_counter() - start_time
        )
        HTTP_REQUESTS.labels(
            method="DELETE", endpoint="/conversations/{id}", status=status_code
        ).inc()

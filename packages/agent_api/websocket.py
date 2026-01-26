"""WebSocket support for real-time conversation."""

from typing import Any

from agent_core import AgentError
from agent_runtime import ConversationState
from fastapi import WebSocket, WebSocketDisconnect  # type: ignore[import-not-found]

from .app import AppState, get_app_state


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and track a WebSocket connection.

        Args:
            websocket: The WebSocket connection
            session_id: The conversation session ID
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            session_id: The conversation session ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific connection.

        Args:
            session_id: The conversation session ID
            message: The message to send
        """
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    def is_connected(self, session_id: str) -> bool:
        """Check if a session has an active connection.

        Args:
            session_id: The conversation session ID

        Returns:
            True if connected, False otherwise
        """
        return session_id in self.active_connections


# Global connection manager
manager = ConnectionManager()


async def _send_initial_state(session_id: str, conversation_state: ConversationState) -> None:
    """Send initial connection state.

    Args:
        session_id: The conversation session ID
        conversation_state: The conversation state
    """
    await manager.send_message(
        session_id,
        {
            "type": "connected",
            "session_id": session_id,
            "greeting": conversation_state.messages[0].content,
            "status": conversation_state.status.value,
        },
    )


async def _handle_user_message(
    state: AppState, session_id: str, conversation_state: ConversationState, content: str
) -> ConversationState:
    """Handle a user message.

    Args:
        state: Application state
        session_id: The conversation session ID
        conversation_state: Current conversation state
        content: User message content

    Returns:
        Updated conversation state
    """
    if state.agent is None:
        return conversation_state

    try:
        response, conversation_state = await state.agent.process_message(
            conversation_state, content
        )

        await manager.send_message(
            session_id,
            {
                "type": "response",
                "content": response,
                "status": conversation_state.status.value,
                "collected_data": conversation_state.get_collected_data(),
            },
        )

        if conversation_state.status.value == "completed":
            await manager.send_message(
                session_id,
                {
                    "type": "completed",
                    "collected_data": conversation_state.get_collected_data(),
                },
            )

    except AgentError as e:
        await manager.send_message(
            session_id,
            {"type": "error", "message": str(e)},
        )

    return conversation_state


async def websocket_conversation(websocket: WebSocket, session_id: str | None = None) -> None:
    """Handle a WebSocket conversation.

    Args:
        websocket: The WebSocket connection
        session_id: Optional existing session ID to continue
    """
    state = get_app_state()

    if state.agent is None:
        await websocket.close(code=1008, reason="Agent not configured")
        return

    if state.store is None:
        await websocket.close(code=1008, reason="Store not initialized")
        return

    # Start or continue conversation
    conversation_state: ConversationState
    if session_id and state.store.get(session_id):
        existing = state.store.get(session_id)
        if existing is not None:
            conversation_state = existing
        else:
            conversation_state = state.agent.start_conversation()
            session_id = conversation_state.session_id
    else:
        conversation_state = state.agent.start_conversation()
        session_id = conversation_state.session_id

    await manager.connect(websocket, session_id)

    try:
        await _send_initial_state(session_id, conversation_state)

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                conversation_state = await _handle_user_message(
                    state, session_id, conversation_state, data.get("content", "")
                )
            elif data.get("type") == "ping":
                await manager.send_message(session_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)


def get_manager() -> ConnectionManager:
    """Get the connection manager.

    Returns:
        The global connection manager instance
    """
    return manager

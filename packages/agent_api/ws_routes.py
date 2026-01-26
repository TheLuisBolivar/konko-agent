"""WebSocket routes for real-time conversation."""

from typing import Optional

from fastapi import APIRouter, WebSocket  # type: ignore[import-not-found]

from .websocket import websocket_conversation

ws_router = APIRouter(tags=["websocket"])


@ws_router.websocket("/ws")  # type: ignore[misc]
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle new WebSocket conversations.

    Args:
        websocket: The WebSocket connection
    """
    await websocket_conversation(websocket)


@ws_router.websocket("/ws/{session_id}")  # type: ignore[misc]
async def websocket_endpoint_with_session(
    websocket: WebSocket, session_id: Optional[str] = None
) -> None:
    """Continue existing conversations via WebSocket.

    Args:
        websocket: The WebSocket connection
        session_id: The existing session ID to continue
    """
    await websocket_conversation(websocket, session_id)

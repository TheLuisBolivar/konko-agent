"""Konko AI Conversational Agent - API Package."""

from .app import AppState, create_app, get_app_state
from .config_routes import config_router
from .models import (
    ConversationResponse,
    ErrorResponse,
    MessageRequest,
    MessageResponse,
    StartConversationResponse,
)
from .routes import router
from .websocket import ConnectionManager, get_manager
from .ws_routes import ws_router

__version__ = "0.1.0"

__all__ = [
    "AppState",
    "ConnectionManager",
    "ConversationResponse",
    "ErrorResponse",
    "MessageRequest",
    "MessageResponse",
    "StartConversationResponse",
    "config_router",
    "create_app",
    "get_app_state",
    "get_manager",
    "router",
    "ws_router",
]

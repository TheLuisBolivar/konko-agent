"""FastAPI Application Factory for Konko AI Agent.

This module provides the FastAPI application factory and configuration
for the conversational agent REST API.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI  # type: ignore[import-not-found]
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-not-found]

from agent_config import AgentConfig, load_config_from_yaml
from agent_core import ConversationalAgent
from agent_runtime import StateStore


class AppState:
    """Application state container."""

    def __init__(self) -> None:
        """Initialize application state."""
        self.agent: Optional[ConversationalAgent] = None
        self.store: Optional[StateStore] = None
        self.config: Optional[AgentConfig] = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan.

    Args:
        app: FastAPI application instance

    Yields:
        None during application lifetime
    """
    # Startup: Initialize resources if not already done
    if app_state.store is None:
        app_state.store = StateStore()

    yield

    # Shutdown: Cleanup resources
    app_state.agent = None
    app_state.store = None
    app_state.config = None


def create_app(
    config: Optional[AgentConfig] = None,
    config_path: Optional[str] = None,
    cors_origins: Optional[list[str]] = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Optional pre-loaded agent configuration
        config_path: Optional path to configuration file
        cors_origins: Optional list of allowed CORS origins

    Returns:
        Configured FastAPI application

    Raises:
        ValueError: If neither config nor config_path is provided
    """
    app = FastAPI(
        title="Konko AI Conversational Agent",
        description="REST API for the Konko AI conversational agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    if cors_origins is None:
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load configuration
    if config is not None:
        app_state.config = config
    elif config_path is not None:
        app_state.config = load_config_from_yaml(config_path)

    # Initialize store if not already done
    if app_state.store is None:
        app_state.store = StateStore()

    # Initialize agent if config is available
    if app_state.config is not None:
        app_state.agent = ConversationalAgent(app_state.config, app_state.store)

    # Register routes
    _register_routes(app)

    return app


def _register_routes(app: FastAPI) -> None:
    """Register API routes.

    Args:
        app: FastAPI application instance
    """
    # Import and include conversation routes
    from .routes import router as conversations_router

    app.include_router(conversations_router)

    @app.get("/health")  # type: ignore[misc]
    async def health_check() -> dict[str, Any]:
        """Health check endpoint.

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "version": "0.1.0",
            "agent_configured": app_state.agent is not None,
        }

    @app.get("/")  # type: ignore[misc]
    async def root() -> dict[str, Any]:
        """Root endpoint.

        Returns:
            Welcome message and API information
        """
        return {
            "message": "Welcome to Konko AI Conversational Agent API",
            "version": "0.1.0",
            "docs_url": "/docs",
        }


def get_app_state() -> AppState:
    """Get the application state.

    Returns:
        Current application state
    """
    return app_state

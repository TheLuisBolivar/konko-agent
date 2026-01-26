"""API routes for configuration management."""

import os
from pathlib import Path
from typing import Any

from agent_config import ConfigurationError, load_config_from_yaml
from agent_core import ConversationalAgent
from fastapi import APIRouter, HTTPException  # type: ignore[import-not-found]
from pydantic import BaseModel, Field

from .app import get_app_state

config_router = APIRouter(prefix="/config", tags=["configuration"])

# Default configs directory
CONFIGS_DIR = Path("configs")


class ConfigLoadRequest(BaseModel):
    """Request model for loading a configuration."""

    config_name: str = Field(
        ...,
        description="Name of the config file (e.g., 'basic_agent' or 'basic_agent.yaml')",
    )


class ConfigInfo(BaseModel):
    """Response model for configuration info."""

    name: str = Field(..., description="Configuration file name")
    path: str = Field(..., description="Full path to configuration file")


class CurrentConfigResponse(BaseModel):
    """Response model for current configuration."""

    loaded: bool = Field(..., description="Whether a configuration is loaded")
    greeting: str | None = Field(None, description="Agent greeting message")
    fields: list[dict[str, Any]] = Field(default_factory=list, description="Fields to collect")
    personality: dict[str, Any] | None = Field(None, description="Agent personality settings")
    llm: dict[str, Any] | None = Field(None, description="LLM configuration")


@config_router.get("/current", response_model=CurrentConfigResponse)  # type: ignore[misc]
async def get_current_config() -> CurrentConfigResponse:
    """Get the currently loaded agent configuration.

    Returns:
        Current configuration details
    """
    state = get_app_state()

    if state.config is None:
        return CurrentConfigResponse(
            loaded=False,
            greeting=None,
            fields=[],
            personality=None,
            llm=None,
        )

    return CurrentConfigResponse(
        loaded=True,
        greeting=state.config.greeting,
        fields=[
            {
                "name": f.name,
                "type": f.field_type,
                "required": f.required,
                "prompt_hint": f.prompt_hint,
            }
            for f in state.config.fields
        ],
        personality={
            "tone": state.config.personality.tone.value,
            "style": state.config.personality.style,
            "formality": state.config.personality.formality.value,
            "emoji_usage": state.config.personality.emoji_usage,
        },
        llm={
            "provider": state.config.llm.provider.value if state.config.llm else None,
            "model": state.config.llm.model_name if state.config.llm else None,
        },
    )


@config_router.get("/list", response_model=list[ConfigInfo])  # type: ignore[misc]
async def list_configs() -> list[ConfigInfo]:
    """List all available configuration files.

    Returns:
        List of available configurations
    """
    configs_dir = os.getenv("CONFIGS_DIR", str(CONFIGS_DIR))
    config_path = Path(configs_dir)

    if not config_path.exists():
        return []

    configs = []
    for file in config_path.glob("*.yaml"):
        configs.append(
            ConfigInfo(
                name=file.stem,
                path=str(file),
            )
        )

    for file in config_path.glob("*.yml"):
        configs.append(
            ConfigInfo(
                name=file.stem,
                path=str(file),
            )
        )

    return sorted(configs, key=lambda c: c.name)


@config_router.put("")  # type: ignore[misc]
async def load_config(request: ConfigLoadRequest) -> dict[str, Any]:
    """Load a new agent configuration.

    This endpoint loads a new configuration and reinitializes the agent.
    Note: This should only be called when no active conversations exist,
    as changing configuration mid-conversation may cause unexpected behavior.

    Args:
        request: Configuration load request with config name

    Returns:
        Success message with loaded configuration info

    Raises:
        HTTPException: If config file not found or invalid
    """
    state = get_app_state()

    # Check for active conversations
    if state.store is not None:
        active_sessions = state.store.get_active_sessions()
        if active_sessions:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot change configuration while {len(active_sessions)} "
                "conversation(s) are active. Please end all conversations first.",
            )

    # Normalize config name
    config_name = request.config_name
    if not config_name.endswith((".yaml", ".yml")):
        config_name = f"{config_name}.yaml"

    # Build config path
    configs_dir = os.getenv("CONFIGS_DIR", str(CONFIGS_DIR))
    config_path = Path(configs_dir) / config_name

    if not config_path.exists():
        # Try .yml extension
        config_path = Path(configs_dir) / config_name.replace(".yaml", ".yml")
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Configuration file '{request.config_name}' not found in {configs_dir}/",
            )

    try:
        # Load new configuration
        new_config = load_config_from_yaml(str(config_path))

        # Update state
        state.config = new_config

        # Reinitialize agent with new config
        if state.store is not None:
            state.agent = ConversationalAgent(state.config, state.store)

        return {
            "message": f"Configuration '{request.config_name}' loaded successfully",
            "config_path": str(config_path),
            "greeting": new_config.greeting,
            "fields_count": len(new_config.fields),
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration: {str(e)}",
        ) from e

"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request model for sending a message."""

    content: str = Field(..., description="The message content from the user")


class MessageResponse(BaseModel):
    """Response model for a message exchange."""

    response: str = Field(..., description="The agent's response")
    session_id: str = Field(..., description="The conversation session ID")
    status: str = Field(..., description="Current conversation status")
    collected_data: dict[str, Any] = Field(
        default_factory=dict, description="Data collected so far"
    )


class ConversationResponse(BaseModel):
    """Response model for conversation state."""

    session_id: str = Field(..., description="The conversation session ID")
    status: str = Field(..., description="Current conversation status")
    messages: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation messages"
    )
    collected_data: dict[str, Any] = Field(
        default_factory=dict, description="Data collected so far"
    )
    started_at: datetime = Field(..., description="When the conversation started")
    updated_at: datetime = Field(..., description="Last update time")


class StartConversationResponse(BaseModel):
    """Response model for starting a conversation."""

    session_id: str = Field(..., description="The new conversation session ID")
    greeting: str = Field(..., description="The agent's greeting message")
    status: str = Field(..., description="Current conversation status")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")

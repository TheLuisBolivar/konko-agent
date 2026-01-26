"""State models for Konko AI Agent runtime.

This module defines the state models used during agent execution,
including conversation state, field collection progress, and message history.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of the message sender."""

    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    """Status of the conversation."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class Message(BaseModel):
    """A single message in the conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique message ID")
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="When the message was sent"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional message metadata"
    )


class FieldValue(BaseModel):
    """A collected field value with validation status."""

    field_name: str = Field(..., description="Name of the field")
    value: Optional[str] = Field(default=None, description="Collected value")
    is_valid: bool = Field(default=False, description="Whether the value passed validation")
    attempts: int = Field(default=0, description="Number of collection attempts")
    last_attempt_timestamp: Optional[datetime] = Field(
        default=None, description="Timestamp of last collection attempt"
    )


class ConversationState(BaseModel):
    """Complete state of an agent conversation."""

    session_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique session identifier"
    )
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE, description="Current conversation status"
    )
    config_id: Optional[str] = Field(
        default=None, description="ID of the agent configuration being used"
    )

    # Message history
    messages: List[Message] = Field(
        default_factory=list, description="Conversation message history"
    )

    # Field collection progress
    collected_fields: Dict[str, FieldValue] = Field(
        default_factory=dict, description="Fields collected so far"
    )
    current_field: Optional[str] = Field(
        default=None, description="Field currently being collected"
    )

    # Escalation tracking
    escalation_triggered: bool = Field(
        default=False, description="Whether escalation has been triggered"
    )
    escalation_reason: Optional[str] = Field(
        default=None, description="Reason for escalation if triggered"
    )
    escalation_policy_id: Optional[str] = Field(
        default=None, description="ID of the policy that triggered escalation"
    )

    # Timestamps
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation started",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp"
    )
    ended_at: Optional[datetime] = Field(default=None, description="When the conversation ended")

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional session metadata"
    )

    def add_message(self, role: MessageRole, content: str, **metadata: Any) -> Message:
        """Add a message to the conversation.

        Args:
            role: Role of the message sender
            content: Message content
            **metadata: Additional metadata for the message

        Returns:
            The created Message object
        """
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message

    def update_field_value(
        self, field_name: str, value: Optional[str], is_valid: bool
    ) -> FieldValue:
        """Update a field value in the state.

        Args:
            field_name: Name of the field to update
            value: New value for the field
            is_valid: Whether the value is valid

        Returns:
            The updated FieldValue object
        """
        if field_name not in self.collected_fields:
            self.collected_fields[field_name] = FieldValue(field_name=field_name)

        field_value = self.collected_fields[field_name]
        field_value.value = value
        field_value.is_valid = is_valid
        field_value.attempts += 1
        field_value.last_attempt_timestamp = datetime.now(timezone.utc)

        self.updated_at = datetime.now(timezone.utc)
        return field_value

    def get_collected_data(self) -> Dict[str, str]:
        """Get all successfully collected field values.

        Returns:
            Dictionary mapping field names to their collected values
        """
        return {
            name: field.value
            for name, field in self.collected_fields.items()
            if field.is_valid and field.value is not None
        }

    def get_missing_fields(self, required_fields: List[str]) -> List[str]:
        """Get list of required fields that haven't been collected.

        Args:
            required_fields: List of required field names

        Returns:
            List of field names that are missing or invalid
        """
        collected = self.get_collected_data()
        return [field for field in required_fields if field not in collected]

    def mark_escalated(self, reason: str, policy_id: Optional[str] = None) -> None:
        """Mark the conversation as escalated.

        Args:
            reason: Reason for escalation
            policy_id: ID of the policy that triggered escalation
        """
        self.status = ConversationStatus.ESCALATED
        self.escalation_triggered = True
        self.escalation_reason = reason
        self.escalation_policy_id = policy_id
        self.ended_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark the conversation as successfully completed."""
        self.status = ConversationStatus.COMPLETED
        self.ended_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """Mark the conversation as failed.

        Args:
            reason: Optional reason for failure
        """
        self.status = ConversationStatus.FAILED
        if reason:
            self.metadata["failure_reason"] = reason
        self.ended_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def get_duration_seconds(self) -> float:
        """Get the duration of the conversation in seconds.

        Returns:
            Duration in seconds, or time since start if not ended
        """
        end_time = self.ended_at or datetime.now(timezone.utc)
        return (end_time - self.started_at).total_seconds()

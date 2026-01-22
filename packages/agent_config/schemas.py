"""Configuration schemas for Konko AI Agent.

This module defines Pydantic models for agent configuration validation.
All configuration must be validated before use to ensure type safety.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Tone(str, Enum):
    """Agent tone options."""

    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    EMPATHETIC = "empathetic"


class Formality(str, Enum):
    """Agent formality level."""

    FORMAL = "formal"
    NEUTRAL = "neutral"
    INFORMAL = "informal"


class AgentPersonality(BaseModel):
    """Configuration for agent personality and communication style."""

    tone: Tone = Field(
        default=Tone.PROFESSIONAL,
        description="Tone of the agent's responses",
    )
    style: str = Field(
        default="concise",
        description="Communication style (e.g., concise, verbose, empathetic)",
    )
    formality: Formality = Field(
        default=Formality.NEUTRAL,
        description="Level of formality in communication",
    )
    emoji_usage: bool = Field(
        default=False,
        description="Whether to use emojis in responses",
    )
    emoji_list: List[str] = Field(
        default_factory=lambda: ["👋", "✅", "📧", "📱", "⚠️"],
        description="List of emojis the agent can use",
    )

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        """Validate style is not empty."""
        if not v or not v.strip():
            raise ValueError("Style cannot be empty")
        return v.strip()


class FieldConfig(BaseModel):
    """Configuration for a single field to collect."""

    name: str = Field(
        ...,
        description="Unique name for this field",
    )
    field_type: str = Field(
        default="text",
        description="Type of field (text, email, phone, etc.)",
    )
    required: bool = Field(
        default=True,
        description="Whether this field is required",
    )
    validation_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern for validation (optional)",
    )
    prompt_hint: Optional[str] = Field(
        default=None,
        description="Hint text for prompting the user",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate field name is not empty and alphanumeric."""
        if not v or not v.strip():
            raise ValueError("Field name cannot be empty")

        name = v.strip()
        if not name.replace("_", "").isalnum():
            raise ValueError("Field name must contain only alphanumeric characters and underscores")

        return name

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v: str) -> str:
        """Validate field type is supported."""
        supported_types = {"text", "email", "phone", "url", "number", "date"}
        if v not in supported_types:
            raise ValueError(f"Field type '{v}' not supported. Must be one of: {supported_types}")
        return v


class EscalationPolicy(BaseModel):
    """Configuration for an escalation policy."""

    enabled: bool = Field(
        default=True,
        description="Whether this escalation policy is active",
    )
    reason: str = Field(
        ...,
        description="Human-readable reason for this escalation policy",
    )
    policy_type: str = Field(
        ...,
        description="Type of escalation policy (keyword, timeout, sentiment, llm_intent)",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Policy-specific configuration",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """Validate reason is not empty."""
        if not v or not v.strip():
            raise ValueError("Escalation reason cannot be empty")
        return v.strip()

    @field_validator("policy_type")
    @classmethod
    def validate_policy_type(cls, v: str) -> str:
        """Validate policy type is supported."""
        supported_types = {"keyword", "timeout", "sentiment", "llm_intent", "completion"}
        if v not in supported_types:
            raise ValueError(f"Policy type '{v}' not supported. Must be one of: {supported_types}")
        return v


class AgentConfig(BaseModel):
    """Complete agent configuration."""

    personality: AgentPersonality = Field(
        default_factory=AgentPersonality,
        description="Agent personality configuration",
    )
    greeting: str = Field(
        default="Hello! I'm here to help collect some information.",
        description="Initial greeting message",
    )
    fields: List[FieldConfig] = Field(
        ...,
        description="List of fields to collect from the user",
    )
    escalation_policies: List[EscalationPolicy] = Field(
        default_factory=list,
        description="List of escalation policies",
    )

    @field_validator("greeting")
    @classmethod
    def validate_greeting(cls, v: str) -> str:
        """Validate greeting is not empty."""
        if not v or not v.strip():
            raise ValueError("Greeting cannot be empty")
        return v.strip()

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: List[FieldConfig]) -> List[FieldConfig]:
        """Validate at least one field is configured."""
        if not v:
            raise ValueError("At least one field must be configured")

        # Check for duplicate field names
        names = [field.name for field in v]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be unique")

        return v

    def get_field_by_name(self, name: str) -> Optional[FieldConfig]:
        """Get a field configuration by name.

        Args:
            name: Field name to search for

        Returns:
            FieldConfig if found, None otherwise
        """
        for field in self.fields:
            if field.name == name:
                return field
        return None

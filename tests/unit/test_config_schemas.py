"""Tests for configuration schemas."""

import pytest
from agent_config.schemas import (
    AgentConfig,
    AgentPersonality,
    EscalationPolicy,
    FieldConfig,
    Formality,
    Tone,
)
from pydantic import ValidationError


class TestAgentPersonality:
    """Tests for AgentPersonality model."""

    def test_default_personality(self):
        """Test default personality values."""
        personality = AgentPersonality()

        assert personality.tone == Tone.PROFESSIONAL
        assert personality.style == "concise"
        assert personality.formality == Formality.NEUTRAL
        assert personality.emoji_usage is False
        assert len(personality.emoji_list) > 0

    def test_custom_personality(self):
        """Test custom personality configuration."""
        personality = AgentPersonality(
            tone=Tone.FRIENDLY,
            style="verbose",
            formality=Formality.INFORMAL,
            emoji_usage=True,
            emoji_list=["😊", "👍"],
        )

        assert personality.tone == Tone.FRIENDLY
        assert personality.style == "verbose"
        assert personality.formality == Formality.INFORMAL
        assert personality.emoji_usage is True
        assert personality.emoji_list == ["😊", "👍"]

    def test_empty_style_fails(self):
        """Test that empty style raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentPersonality(style="")

        assert "Style cannot be empty" in str(exc_info.value)

    def test_whitespace_style_fails(self):
        """Test that whitespace-only style raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentPersonality(style="   ")

        assert "Style cannot be empty" in str(exc_info.value)


class TestFieldConfig:
    """Tests for FieldConfig model."""

    def test_minimal_field_config(self):
        """Test minimal field configuration."""
        field = FieldConfig(name="email")

        assert field.name == "email"
        assert field.field_type == "text"
        assert field.required is True
        assert field.validation_pattern is None
        assert field.prompt_hint is None

    def test_complete_field_config(self):
        """Test complete field configuration."""
        field = FieldConfig(
            name="user_email",
            field_type="email",
            required=True,
            validation_pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            prompt_hint="What's your email address?",
        )

        assert field.name == "user_email"
        assert field.field_type == "email"
        assert field.required is True
        assert field.validation_pattern is not None
        assert field.prompt_hint == "What's your email address?"

    def test_empty_field_name_fails(self):
        """Test that empty field name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FieldConfig(name="")

        assert "Field name cannot be empty" in str(exc_info.value)

    def test_invalid_field_name_fails(self):
        """Test that invalid field name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FieldConfig(name="user-email")  # Hyphens not allowed

        assert "alphanumeric" in str(exc_info.value)

    def test_unsupported_field_type_fails(self):
        """Test that unsupported field type raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FieldConfig(name="custom", field_type="invalid_type")

        assert "not supported" in str(exc_info.value)

    def test_supported_field_types(self):
        """Test all supported field types."""
        supported_types = ["text", "email", "phone", "url", "number", "date"]

        for field_type in supported_types:
            field = FieldConfig(name=f"test_{field_type}", field_type=field_type)
            assert field.field_type == field_type


class TestEscalationPolicy:
    """Tests for EscalationPolicy model."""

    def test_keyword_escalation_policy(self):
        """Test keyword-based escalation policy."""
        policy = EscalationPolicy(
            enabled=True,
            reason="User requested human agent",
            policy_type="keyword",
            config={"keywords": ["human", "agent", "help"]},
        )

        assert policy.enabled is True
        assert policy.reason == "User requested human agent"
        assert policy.policy_type == "keyword"
        assert "keywords" in policy.config

    def test_timeout_escalation_policy(self):
        """Test timeout-based escalation policy."""
        policy = EscalationPolicy(
            enabled=True,
            reason="Conversation timeout",
            policy_type="timeout",
            config={"max_duration_seconds": 300},
        )

        assert policy.policy_type == "timeout"
        assert policy.config["max_duration_seconds"] == 300

    def test_disabled_escalation_policy(self):
        """Test disabled escalation policy."""
        policy = EscalationPolicy(enabled=False, reason="Test policy", policy_type="keyword")

        assert policy.enabled is False

    def test_empty_reason_fails(self):
        """Test that empty reason raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            EscalationPolicy(enabled=True, reason="", policy_type="keyword")

        assert "reason cannot be empty" in str(exc_info.value)

    def test_unsupported_policy_type_fails(self):
        """Test that unsupported policy type raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            EscalationPolicy(enabled=True, reason="Test", policy_type="invalid_type")

        assert "not supported" in str(exc_info.value)

    def test_supported_policy_types(self):
        """Test all supported policy types."""
        supported_types = ["keyword", "timeout", "sentiment", "llm_intent", "completion"]

        for policy_type in supported_types:
            policy = EscalationPolicy(
                enabled=True, reason=f"Test {policy_type}", policy_type=policy_type
            )
            assert policy.policy_type == policy_type


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_minimal_agent_config(self):
        """Test minimal agent configuration."""
        config = AgentConfig(fields=[FieldConfig(name="name")])

        assert len(config.fields) == 1
        assert config.fields[0].name == "name"
        assert config.greeting  # Has default value
        assert config.personality is not None
        assert len(config.escalation_policies) == 0

    def test_complete_agent_config(self):
        """Test complete agent configuration."""
        config = AgentConfig(
            personality=AgentPersonality(
                tone=Tone.FRIENDLY,
                emoji_usage=True,
            ),
            greeting="Hi there! 👋",
            fields=[
                FieldConfig(name="name", prompt_hint="What's your name?"),
                FieldConfig(
                    name="email",
                    field_type="email",
                    prompt_hint="What's your email?",
                ),
            ],
            escalation_policies=[
                EscalationPolicy(
                    enabled=True,
                    reason="User requested help",
                    policy_type="keyword",
                    config={"keywords": ["help"]},
                )
            ],
        )

        assert config.personality.tone == Tone.FRIENDLY
        assert config.greeting == "Hi there! 👋"
        assert len(config.fields) == 2
        assert len(config.escalation_policies) == 1

    def test_no_fields_fails(self):
        """Test that config without fields raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(fields=[])

        assert "At least one field must be configured" in str(exc_info.value)

    def test_empty_greeting_fails(self):
        """Test that empty greeting raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(greeting="", fields=[FieldConfig(name="name")])

        assert "Greeting cannot be empty" in str(exc_info.value)

    def test_duplicate_field_names_fails(self):
        """Test that duplicate field names raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                fields=[
                    FieldConfig(name="email"),
                    FieldConfig(name="email"),  # Duplicate
                ]
            )

        assert "Field names must be unique" in str(exc_info.value)

    def test_get_field_by_name(self):
        """Test retrieving field by name."""
        config = AgentConfig(
            fields=[
                FieldConfig(name="name"),
                FieldConfig(name="email", field_type="email"),
            ]
        )

        name_field = config.get_field_by_name("name")
        assert name_field is not None
        assert name_field.name == "name"

        email_field = config.get_field_by_name("email")
        assert email_field is not None
        assert email_field.field_type == "email"

        missing_field = config.get_field_by_name("nonexistent")
        assert missing_field is None


class TestEnums:
    """Tests for enum types."""

    def test_tone_enum_values(self):
        """Test Tone enum values."""
        assert Tone.FRIENDLY == "friendly"
        assert Tone.PROFESSIONAL == "professional"
        assert Tone.CASUAL == "casual"
        assert Tone.EMPATHETIC == "empathetic"

    def test_formality_enum_values(self):
        """Test Formality enum values."""
        assert Formality.FORMAL == "formal"
        assert Formality.NEUTRAL == "neutral"
        assert Formality.INFORMAL == "informal"
